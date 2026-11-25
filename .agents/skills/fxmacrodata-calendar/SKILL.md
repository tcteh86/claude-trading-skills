---
name: fxmacrodata-calendar
description: Check official macro release dates and event risk for a currency using the FXMacroData calendar when the user requests current provider data.
---

Read the [canonical calendar contract](../../../skills/fxmacrodata-calendar/SKILL.md). From the repository root, use the following command for an authorized live USD calendar lookup.

```sh
python -m investment_intelligence skill --live fxmacrodata-calendar --currency usd --min-tier 1
```

Use the process binding `FXMACRODATA_API_KEY` for authenticated access. Keep the value out of chat, command arguments and reports. Read accepted event timestamps and quality flags from the JSON result. A provider failure leaves event risk unverified. For an offline walkthrough use the [fixture workflow](../offline-market-research/SKILL.md) and identify the fixture date explicitly.
