"""Exercise repository discovery metadata, native CLI delegation and fixture replay."""

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from investment_intelligence import __main__ as runner

ROOT = runner.ROOT


def invoke(*args, **kwargs):
    return subprocess.run(
        [sys.executable, "-m", "investment_intelligence", *map(str, args)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        **kwargs,
    )


def test_discovery_links_resolve_to_canonical_contracts():
    catalog = yaml.safe_load((ROOT / "skills-index.yaml").read_text(encoding="utf-8"))
    ids = {row["id"] for row in catalog["skills"]}
    wrappers = {p.parent.name: p for p in (ROOT / ".agents/skills").glob("*/SKILL.md")}
    assert wrappers.keys() == {
        *runner.SKILL_SCRIPTS,
        *runner.CUSTOM_SKILLS,
        "offline-market-research",
    }
    for name, path in wrappers.items():
        _, metadata, body = path.read_text(encoding="utf-8").split("---", 2)
        fields = yaml.safe_load(metadata)
        assert fields["name"] == name and fields["description"].strip()
        links = [(path.parent / s).resolve() for s in re.findall(r"\]\(([^)]+)\)", body)]
        assert all(p.exists() for p in links)
        if name in runner.SKILL_SCRIPTS:
            assert name in ids
            assert ROOT / "skills" / name / "SKILL.md" in links
        elif name in runner.CUSTOM_SKILLS:
            assert name not in ids and links
        else:
            for workflow in runner.WORKFLOWS:
                assert ROOT / "workflows" / f"{workflow}.yaml" in links


@pytest.mark.parametrize("name", runner.SKILL_SCRIPTS)
def test_individual_help_uses_native_parser(name):
    native = ROOT / "skills" / name / "scripts" / runner.SKILL_SCRIPTS[name]
    help_text = subprocess.check_output([sys.executable, str(native), "--help"], text=True)
    actual = invoke("skill", name, "--help", check=True)
    assert actual.stdout == help_text


def test_live_opt_in_and_environment(monkeypatch):
    marker = "SYNTHETIC-credential-marker"
    monkeypatch.setenv("FXMACRODATA_API_KEY", marker)
    monkeypatch.setenv("FMP_API_KEY", marker)
    assert marker not in runner.child_environment().values()
    assert runner.child_environment(calendar=True)["FXMACRODATA_API_KEY"] == marker
    assert "FMP_API_KEY" not in runner.child_environment(calendar=True)
    refused = invoke("skill", "fxmacrodata-calendar", "--currency", "usd")
    assert refused.returncode and "--live" in refused.stderr
    # Invalid currency fails before transport. The native validation is exercised.
    invalid = invoke("skill", "--live", "fxmacrodata-calendar", "--currency", "invalid")
    assert invalid.returncode and "3-letter" in invalid.stderr
    assert marker not in invalid.stdout + invalid.stderr + refused.stdout + refused.stderr


@pytest.mark.parametrize("workflow", runner.WORKFLOWS)
def test_full_workflow_matches_canonical_artifacts(workflow, tmp_path):
    marker = "SYNTHETIC-unused-marker"
    run = invoke(
        "workflow",
        workflow,
        "--output-parent",
        tmp_path / "research results",
        env={**os.environ, "FMP_API_KEY": marker},
        check=True,
    )
    bundle = Path(run.stdout.strip())
    receipt = json.loads((bundle / "run.json").read_bytes())
    manifest = yaml.safe_load((bundle / "artifacts/manifest.yaml").read_bytes())
    assert manifest["status"] == "completed" and receipt["variant"] == "full-path"
    assert receipt["workflow_id"] == workflow
    definition = yaml.safe_load((ROOT / "workflows" / f"{workflow}.yaml").read_bytes())
    assert manifest["completed_steps"] == [s["step"] for s in definition["steps"]]
    spec_dir = ROOT / "examples/workflows" / workflow
    spec = yaml.safe_load((spec_dir / "replay.yaml").read_bytes())
    assert receipt["as_of"] == spec["fixed_timestamp"]
    for path in spec["inputs"].values():
        fixture = spec_dir / path
        key = fixture.relative_to(ROOT).as_posix()
        assert receipt["inputs_sha256"][key] == hashlib.sha256(fixture.read_bytes()).hexdigest()
    golden = spec_dir / spec["variants"]["full-path"]["golden_dir"]
    assert set(receipt["artifacts_sha256"]) == {
        path.relative_to(golden).as_posix() for path in golden.rglob("*") if path.is_file()
    }
    for filename, checksum in receipt["artifacts_sha256"].items():
        actual = (bundle / "artifacts" / filename).read_bytes()
        assert actual == (golden / filename).read_bytes()
        assert hashlib.sha256(actual).hexdigest() == checksum
    assert marker not in run.stdout + run.stderr
    assert all(marker.encode() not in f.read_bytes() for f in bundle.rglob("*") if f.is_file())


def test_repeatable_workflow_and_individual_handoff(tmp_path):
    args = ("workflow", "market-regime-daily", "--output-parent", tmp_path)
    first = Path(invoke(*args, check=True).stdout.strip())
    second = Path(invoke(*args, check=True).stdout.strip())
    assert first != second
    assert (first / "run.json").read_bytes() == (second / "run.json").read_bytes()
    files = first / "artifacts"
    expected = json.loads((files / "04_exposure_decision.json").read_bytes())
    individual = tmp_path / "individual"
    invoke(
        "skill",
        "exposure-coach",
        "--breadth",
        files / "01_market_breadth_report.json",
        "--uptrend",
        files / "02_uptrend_report.json",
        "--top-risk",
        files / "03_top_risk_report.json",
        "--as-of",
        expected["input_lineage"]["evaluation_at"],
        "--run-id",
        expected["input_lineage"]["run_id"],
        "--require-provenance",
        "--json-only",
        "--output-dir",
        individual,
        check=True,
    )
    actual = json.loads(next(individual.glob("*.json")).read_bytes())
    # Native individual reports stamp their actual creation time.
    assert actual.pop("generated_at") and expected.pop("generated_at")
    assert actual == expected


def test_invalid_destinations_and_ids():
    protected = invoke("workflow", "market-regime-daily", "--output-parent", ROOT)
    assert protected.returncode and "outside the checkout" in protected.stderr
    assert invoke("skill", "../other.py").returncode
    assert invoke("workflow", "../other.yaml").returncode


def test_required_only_variant_reports_skipped_optional_evidence(tmp_path):
    run = invoke(
        "workflow",
        "market-regime-daily",
        "--variant",
        "required-only",
        "--output-parent",
        tmp_path,
        check=True,
    )
    artifacts = Path(run.stdout.strip()) / "artifacts"
    manifest = yaml.safe_load((artifacts / "manifest.yaml").read_bytes())
    assert manifest["completed_steps"] == [1, 2, 4]
    assert not (artifacts / "03_top_risk_report.json").exists()


def test_failed_replay_publishes_no_bundle(monkeypatch, tmp_path):
    def failed(*args, **kwargs):
        return subprocess.CompletedProcess(args, returncode=1, stdout="", stderr="invalid fixture")

    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: "test-revision")
    monkeypatch.setattr(subprocess, "run", failed)
    with pytest.raises(ValueError, match="invalid fixture"):
        runner.run_workflow("market-regime-daily", "full-path", tmp_path)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("echo", [None, "stdout", "stderr"])
def test_authenticated_dispatch_keeps_credentials_private(monkeypatch, capsys, echo):
    marker = "synthetic-calendar-binding"
    monkeypatch.setenv("FXMACRODATA_API_KEY", marker)
    monkeypatch.setenv("BROKER_SECRET", "unused")
    monkeypatch.setattr(
        sys, "argv", ["runner", "skill", "--live", "fxmacrodata-calendar", "--currency", "usd"]
    )

    def calendar(command, *, env, capture_output):
        assert capture_output
        assert command == [
            sys.executable,
            str(ROOT / "skills/fxmacrodata-calendar/scripts/fetch_calendar.py"),
            "--currency",
            "usd",
        ]
        assert env["FXMACRODATA_API_KEY"] == marker
        assert "BROKER_SECRET" not in env
        stdout = marker.encode() if echo == "stdout" else b""
        stderr = marker.encode() if echo == "stderr" else b"provider unavailable"
        return subprocess.CompletedProcess(command, 23, stdout, stderr)

    monkeypatch.setattr(subprocess, "run", calendar)
    assert runner.main() == (1 if echo else 23)
    stdout, stderr = capsys.readouterr()
    assert marker not in stdout + stderr
    assert "withheld" in stderr if echo else "provider unavailable" in stderr
