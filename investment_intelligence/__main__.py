"""Run selected canonical skills and fictional market research workflows."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILL_SCRIPTS = {
    "exposure-coach": "calculate_exposure.py",
    "fxmacrodata-calendar": "fetch_calendar.py",
}
CUSTOM_SKILLS = {"multibagger-discovery-screener": "investment_intelligence.multibagger"}
WORKFLOWS = ("market-regime-daily", "earnings-weekly")


def child_environment(*, calendar: bool = False) -> dict[str, str]:
    """Pass OS runtime settings and only the selected provider's binding."""
    names = {"PATH", "SYSTEMROOT", "WINDIR", "TMP", "TEMP", "TMPDIR", "LANG", "LC_ALL", "TZ"}
    if calendar:
        names.update(
            {"FXMACRODATA_API_KEY", "SSL_CERT_FILE", "SSL_CERT_DIR", "HTTPS_PROXY", "NO_PROXY"}
        )
    return {
        **{k: v for k, v in os.environ.items() if k.upper() in names},
        "PYTHONIOENCODING": "utf-8",
    }


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_skill(skill: str, options: list[str], *, live: bool) -> int:
    if skill in CUSTOM_SKILLS:
        return subprocess.run(
            [sys.executable, "-m", CUSTOM_SKILLS[skill], *options],
            env=child_environment(),
            cwd=Path.cwd(),
        ).returncode
    script = ROOT / "skills" / skill / "scripts" / SKILL_SCRIPTS[skill]
    command = [sys.executable, str(script), *options]
    environment = child_environment(calendar=live)
    key = environment.get("FXMACRODATA_API_KEY", "").strip()
    if not key:
        return subprocess.run(command, env=environment).returncode

    # An authenticated provider can echo a credential even in a successful payload.
    result = subprocess.run(command, env=environment, capture_output=True)
    if key.encode() in result.stdout or key.encode() in result.stderr:
        print("Calendar response withheld because it contained the credential.", file=sys.stderr)
        return 1
    sys.stdout.buffer.write(result.stdout)
    sys.stderr.buffer.write(result.stderr)
    return result.returncode


def run_workflow(workflow: str, variant: str, parent: Path) -> Path:
    """Reserve a unique directory and publish a receipt only for a completed run."""
    parent = parent.resolve()
    if parent.is_relative_to(ROOT):
        raise ValueError("choose an output parent outside the checkout")
    spec = ROOT / "examples" / "workflows" / workflow / "replay.yaml"
    config = yaml.safe_load(spec.read_text(encoding="utf-8"))
    fixture_dir = (spec.parent / "replay-inputs").resolve()
    fixtures = [(spec.parent / name).resolve() for name in config["inputs"].values()]
    if any(not path.is_relative_to(fixture_dir) for path in fixtures):
        raise ValueError("fixture path outside the workflow's replay-inputs directory")
    sources = [
        spec,
        ROOT / "workflows" / f"{workflow}.yaml",
        ROOT / "uv.lock",
        Path(__file__),
        *fixtures,
    ]
    inputs = {p.relative_to(ROOT).as_posix(): digest(p) for p in sources}
    revision = subprocess.check_output(
        ["git", "rev-parse", "--verify", "HEAD"], cwd=ROOT, text=True
    ).strip()
    parent.mkdir(parents=True, exist_ok=True)
    bundle = Path(tempfile.mkdtemp(prefix=f"{workflow}-", dir=parent))
    artifacts = bundle / "artifacts"
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "workflow_replay.py"),
                "run",
                "--spec",
                str(spec),
                "--variant",
                variant,
                "--output-dir",
                str(artifacts),
            ],
            cwd=ROOT,
            env=child_environment(),
            capture_output=True,
            encoding="utf-8",
            check=False,
        )
        if result.returncode:
            raise ValueError(f"offline replay failed: {result.stderr.strip()}")
        manifest = yaml.safe_load((artifacts / "manifest.yaml").read_text(encoding="utf-8"))
        if manifest["status"] != "completed":
            raise ValueError(f"offline replay stopped with status {manifest['status']}")
        if any(digest(ROOT / name) != expected for name, expected in inputs.items()):
            raise ValueError("a replay source changed during execution")
        receipt = {
            "schema_version": 1,
            "source": "synthetic fixtures",
            "as_of": config["fixed_timestamp"],
            "git_head": revision,
            "inputs_sha256": inputs,
            "artifacts_sha256": {
                p.relative_to(artifacts).as_posix(): digest(p)
                for p in sorted(artifacts.rglob("*"))
                if p.is_file()
            },
            "workflow_id": workflow,
            "variant": variant,
        }
        (bundle / "run.json").write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
        )
    except BaseException:
        shutil.rmtree(bundle)
        raise
    return bundle


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    replay = commands.add_parser("workflow", help="run a canonical offline fixture workflow")
    replay.add_argument("id", choices=WORKFLOWS)
    replay.add_argument("--variant", choices=("required-only", "full-path"), default="full-path")
    replay.add_argument("--output-parent", type=Path, default=Path(tempfile.gettempdir()))
    skill = commands.add_parser("skill", help="invoke a selected canonical skill CLI")
    skill.add_argument(
        "--live", action="store_true", help="enable the FXMacroData calendar request"
    )
    skill.add_argument("id", choices=(*SKILL_SCRIPTS, *CUSTOM_SKILLS))
    skill.add_argument("options", nargs=argparse.REMAINDER, help="canonical CLI arguments")
    args = parser.parse_args()
    if args.command == "skill":
        calendar = args.id == "fxmacrodata-calendar"
        if args.live and not calendar:
            parser.error("--live applies only to fxmacrodata-calendar")
        if calendar and not args.live and args.options not in (["--help"], ["-h"]):
            parser.error("fxmacrodata-calendar requires --live before the skill ID")
        return run_skill(args.id, args.options, live=args.live)

    try:
        print(run_workflow(args.id, args.variant, args.output_parent))
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"Workflow failed: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
