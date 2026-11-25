---
name: exposure-coach
description: Assess equity market posture from supplied breadth, uptrend and risk reports. Use for questions about exposure ceilings, missing evidence or confidence in a posture assessment.
---

Read the [canonical Exposure Coach instructions](../../../skills/exposure-coach/SKILL.md). Resolve their references relative to that skill directory. Use local JSON handoffs and the repository Python environment. Inspect supported flags from the checkout root with `python -m investment_intelligence skill exposure-coach --help`.

Pass the available reports to that command. Use a private output directory. For a dated run with supplied provenance, pass the matching run ID and timezone-aware cutoff using the canonical strict-mode flags. Report excluded or missing evidence and the confidence cap. If the user wants a demonstration, invoke the [offline research workflow](../offline-market-research/SKILL.md) and label its output synthetic. Never treat a posture label as authorization for an order.
