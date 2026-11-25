# Codex compatibility

The fork exposes four Codex skills through one Python entry point. You can replay two upstream research workflows, run Exposure Coach on supplied reports, request live events through FXMacroData, or screen a dated company cohort with the fork's multibagger discovery skill.

## Install and discover

Use a trusted Git checkout, Git, uv, Python 3.11.5 through 3.13, and a Codex client with repository skill support. From the checkout root, install the repository's locked development and CI extras. The following commands work in Bash and PowerShell.

```sh
uv sync --locked --no-install-project --extra dev --extra ci
uv run --no-sync python -m investment_intelligence --help
```

Start a new Codex session from the checkout root after adding the wrappers. Use the skill picker or invoke a skill by name. For example, ask “Use $offline-market-research to run the synthetic market-regime workflow and explain its confidence.” In a prompt, the dollar-prefixed name refers to the Codex skill. With the project virtual environment active, commands can start with `python`. Otherwise use `uv run --no-sync python` as shown below. On cloud machines with a read-only uv home cache, use the configured writable cache or put `--no-cache` immediately after `uv`. For example, `uv --no-cache run --no-sync python -m investment_intelligence --help` works with the prepared environment.

| Codex name | Execution and evidence |
|---|---|
| `$multibagger-discovery-screener` | Screens a dated listing cohort with primary evidence, financial risk checks and diluted growth scenarios. [Usage and snapshot contract](MULTIBAGGER_DISCOVERY.md) |
| `$offline-market-research` | Runs `market-regime-daily` or `earnings-weekly` from their versioned replay specifications and bundled fictional inputs. |
| `$exposure-coach` | Runs the canonical calculator on local JSON handoffs. Missing or rejected evidence affects the native result. |
| `$fxmacrodata-calendar` | Fetches current calendar events for an explicit live lookup. The existing client validates provider quality metadata and reads credentials from the environment. |

Codex loads short instructions from `.agents/skills/`. Existing skill IDs and domain instructions remain in `skills-index.yaml` and `skills/<id>/SKILL.md`. The wrappers refer to those files and run the repository interpreter. A request for additional evidence must identify available inputs and permitted tools. Claude-specific session prompts, WebSearch and MCP integrations are unnecessary for these entry points. Workflow steps use the existing offline replay harness and carry their native or fixture-backed execution mode into the manifest.

## Offline demonstration

```sh
uv run --no-sync python -m investment_intelligence workflow market-regime-daily --output-parent ../codex-research
uv run --no-sync python -m investment_intelligence workflow earnings-weekly --output-parent ../codex-research
```

Each command prints a new bundle directory. Read `run.json`, then `artifacts/manifest.yaml` and the final decision JSON in that directory. The default `full-path` variant includes optional steps where present. Use `--variant required-only` for the shorter upstream variant. If the parent is omitted, the operating system's temporary directory is used. Choose a private parent outside the checkout for retained results. Repeated or concurrent runs receive separate directories.

- **Market regime.** Three upstream scoring APIs process fictional breadth, uptrend and top-risk components. Exposure Coach consumes all three reports. At the bundled cutoff of 2026-01-15 13:08 UTC the expected composite score is 55.9, the exposure ceiling is 57%, and confidence is MEDIUM. The result identifies missing regime evidence. These values describe the synthetic scenario.
- **Weekly earnings.** The workflow passes fictional provider data through the earnings analyzer and PEAD screener, then applies the fixture's technical review, sizing, journal and discipline checks. The final artifact records a manual decision for fictional symbol EXMA. The manifest identifies manual inputs and computed outputs.
- **Traceability.** The manifest records the replay steps and execution modes. The receipt records the fixed evaluation time, Git HEAD, and SHA-256 digests for the workflow definition, replay spec, fixture files, runner, lockfile and published artifacts. Compare `run.json` and the artifact bytes between runs of the same checkout and variant. Preserve the checkout and any local edits for exact replay. The output directory name is intentionally unique.

## Run a single skill

Use the native help to see supported report inputs and flags.

```sh
uv run --no-sync python -m investment_intelligence skill exposure-coach --help
uv run --no-sync python -m investment_intelligence skill fxmacrodata-calendar --help
uv run --no-sync python -m investment_intelligence skill multibagger-discovery-screener --help
```

For example, change the paths beginning with `BUNDLE` to the first demo's output directory. This runs the selected skill independently on the same evidence.

```sh
uv run --no-sync python -m investment_intelligence skill exposure-coach --breadth BUNDLE/artifacts/01_market_breadth_report.json --uptrend BUNDLE/artifacts/02_uptrend_report.json --top-risk BUNDLE/artifacts/03_top_risk_report.json --run-id fictional-market-regime-daily-run-001 --as-of 2026-01-15T13:08:00+00:00 --require-provenance --json-only --output-dir ../codex-research/individual
```

The decision fields match the workflow artifact. The single-skill CLI stamps its actual creation time and uses its native filenames. Use the workflow command for byte-reproducible fixture outputs.

## Optional live calendar

The offline workflows require no account, network fetch, or API key after installation. For a requested live calendar lookup, enable network access to `api.fxmacrodata.com`. Public USD data and authenticated coverage depend on provider availability and terms. Configure `FXMACRODATA_API_KEY` in environment settings or a local secret manager for authenticated requests. The native client sends it in the request header and refuses redirects. Keep values out of prompts, arguments, logs and files in Git. Other provider and broker credentials are unnecessary.

```sh
uv run --no-sync python -m investment_intelligence skill --live fxmacrodata-calendar --currency usd --min-tier 1
```

A nonzero provider exit leaves event risk unverified. The live response reflects the provider's data at request time. Offline workflows always use their local fixtures, including when provider credentials exist.

## Verification and maintenance

```sh
uv run --no-sync python -m pytest -q tests/custom
uv run --no-sync python scripts/validate_skills_index.py
uv run --no-sync python scripts/validate_skillsets.py
```

The fork compatibility CI runs the first check on Linux, macOS and Windows. It verifies the links from discovery metadata to the canonical skill catalog, native CLI behavior, credential isolation, both full workflow outputs against upstream goldens, repeatability and failure cleanup. Upstream tests keep their existing matrix and entry points. After pulling upstream, review changed contracts and golden artifacts before adapting a wrapper. For a new Codex skill, reference its canonical instructions, identify its data and credential needs, and test the execution path with the same interpreter and controlled fixtures.

The dispatcher maps supported IDs to canonical Python entry points and records workflow receipts. The fork's tests and CI job live outside the upstream skill and test catalogs. [Dispatcher](../../investment_intelligence/__main__.py) · [Codex wrappers](../../.agents/skills) · [Regression tests](../../tests/custom/test_codex_compatibility.py) · [Compatibility CI](../../.github/workflows/codex-compatibility.yml)

## Validation history

After the screener was added, Codex discovered all four skills and the fork suite passed 74 tests on Linux. The screener guide records its deterministic replay, upstream test results and platform coverage. [Screener verification](MULTIBAGGER_DISCOVERY.md#verification)

At the initial Phase 1 milestone on Linux with Python 3.13.5, the full upstream pytest suite returned 17,606 passes, one failure, three skips and 13 passing subtests, matching the baseline. The pre-existing theme-detector missing-calendar test passed when rerun alone. The 13 fork compatibility tests passed, along with 354 isolated Exposure Coach tests and 115 FXMacroData tests. Codex CLI 0.172.0-alpha.2 listed the three skills available at that milestone as enabled. Both demo bundles matched their upstream golden artifacts. Linux system-call tracing recorded zero IPv4 or IPv6 connect calls in either demo process tree. Native Windows and macOS execution and live provider access await separate verification.
