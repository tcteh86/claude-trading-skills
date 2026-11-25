"""Screen a verified listing snapshot for evidence-backed asymmetric upside."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

from . import upstream
from .contracts import config, read_json
from .engine import screen


def json_digest(value):
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def implementation_digests():
    root = upstream.SKILLS.parent
    files = [
        *Path(__file__).parent.glob("*.py"),
        *(
            upstream.GROWTH / name
            for name in ("evaluation_common.py", "evaluation_financials.py", "skill_version.py")
        ),
        *(
            Path(module.__file__)
            for module in (upstream.flow, upstream.quality, upstream.technical)
        ),
    ]
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(
            path.read_text(encoding="utf-8").encode("utf-8")
        ).hexdigest()
        for path in files
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", type=Path, required=True, help="point-in-time JSON research snapshot"
    )
    parser.add_argument(
        "--config", type=Path, help="JSON overrides for the bundled screening policy"
    )
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        help="root of archived primary-source extracts (default: input directory)",
    )
    args = parser.parse_args()
    try:
        snapshot = read_json(args.input)
        settings = config(read_json(args.config) if args.config else {})
        result = screen(snapshot, settings, args.evidence_dir or args.input.resolve().parent)
        result["snapshot_sha256"] = json_digest(snapshot)
        result["configuration_sha256"] = json_digest(settings)
        result["calculation_files_sha256"] = implementation_digests()
        output = json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
    except (OSError, KeyError, ValueError, TypeError, ArithmeticError, AttributeError) as exc:
        print(f"Invalid screening input: {exc}", file=sys.stderr)
        return 2
    sys.stdout.buffer.write((output + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
