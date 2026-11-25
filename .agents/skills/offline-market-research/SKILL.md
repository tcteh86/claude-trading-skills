---
name: offline-market-research
description: Run a reproducible fictional market-regime or weekly earnings research workflow, inspect its skill handoffs, and explain the evidence behind its final decision.
---

Work from the repository root with its Python environment active. For a market posture review, run the command below. For an earnings research walkthrough, substitute `earnings-weekly`.

```sh
python -m investment_intelligence workflow market-regime-daily
```

Read `run.json` and `artifacts/manifest.yaml` in the printed directory. Follow the final artifact listed in the manifest. Explain the decision, cutoff, missing inputs, confidence, and the limits of synthetic evidence. Distinguish handoffs computed by a skill from manual judgments supplied as fixtures. Describe any blocked result and stop at human review.

The canonical [market-regime workflow](../../../workflows/market-regime-daily.yaml) and [earnings workflow](../../../workflows/earnings-weekly.yaml) define the steps. Read the corresponding `skills/<id>/SKILL.md` for domain interpretation. See the [usage guide](../../../docs/custom/CODEX_COMPATIBILITY.md) for configuration and replay options.
