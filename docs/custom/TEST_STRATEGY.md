# Test strategy

Validate the legacy interfaces, the fork's deterministic decisions, the data contract and the empirical method independently. Keep standard CI offline and use synthetic or rights-cleared fixtures. Record the runtime, config hash, data manifest, result counts and any skipped or blocked checks.

| Layer | Representative cases | Gate |
|---|---|---|
| Upstream regression | CI matrix rows, generated docs and packages, manifest validators, workflow replay, clean-room packaged imports and supported Python/OS matrix. | Changes preserve upstream public outputs or document any separately approved change. |
| Provider and normalization | Rate limit, auth/plan denial, truncated paging, schema/type drift, malformed values, staleness, duplicate symbols, ticker reuse, FX inversion and conflicting sources. | Typed failures, bounded retries and deterministic blocked reasons. No key or raw account payload in diagnostics. |
| As-of data | Future revisions, after-hours filing, DST/holiday, delisted names, splits, special dividends, rights, suspensions, SGX sessions and crypto UTC boundaries. | Fixtures prove no future observations leak and preserve correct timestamps and adjustments. |
| Financial golden cases | Independent hand or spreadsheet reference for valuation sensitivity, net debt and diluted shares, recurring vs special distributions, AFFO/DPU, stress refinance, fees and FX-adjusted portfolio returns. Include zero/negative denominators and inconsistent currencies. | Document expected values, units, rounding policy and tolerances. Critical uncertainties block decisions. |
| Decision semantics | Missing fields, contradictory evidence, sparse providers, coverage downgrade, tie resolution and incomparable cohorts. | Rankings contain eligible records only. Attractiveness, risk and confidence remain independent. Unsupported reports are clearly blocked. |
| Offline E2E | CLI and future Codex wrapper use the same versioned artifacts. Run a US screen/dossier, then each new workflow's happy and blocked paths with a fixed clock. | Stable deterministic report after volatile metadata is controlled. Linked provenance resolves and every terminal state is visible. |
| Safety and privacy | Verify outbound host policy, bounded parser behavior, untrusted evidence handling, denied actions, redaction, local-only imports and permitted export fields. | No order capability, uncontrolled external action, credentials or holdings in logs or artifacts. |
| Scheduled provider canaries | Approved minimal requests with schema, currency, freshness and coverage assertions. Test retry budget. | Quarantined from PR gates. Live failures record provider and dataset and block affected claims until resolved. |

## Empirical protocol

1. Freeze the universe rules, candidate labels, metrics, costs, tuning budget and holdout before scoring. Define the multibagger horizon and dividend-inclusive return convention, and include merged, suspended and delisted cases.
2. Use a point-in-time listing universe and as-reported financials with actual availability lags. Verify timestamps at every join and model next tradable fills with spreads, impact, fees and liquidity limits. Use venue-specific trading calendars.
3. Use rolling or expanding walk-forward evaluation with a gap or purge for overlapping labels and an untouched final holdout. Log all trials and report uncertainty, multiple-testing treatment, regime sensitivity and failure modes. Compare to simple size/sector/liquidity-matched baselines and investable benchmarks.
4. Compare calibration, coverage, candidate hit rate and false positives, turnover, drawdown and benchmark-relative performance. Show base rates, top-candidate counts and attrition through data gates. Keep explanatory case studies separate from performance evidence.
5. Require replication by replay from versioned inputs. Flag unverified data coverage and keep the workflow research-only until the required evidence is available.

## Phase 0 checks

Check the eight deliverables, internal links, implementation dependencies, and Git diff against the baseline. Reuse onboarding's existing tests as environment evidence. Full CI, live canaries and empirical validation are separate from Phase 0 acceptance.
