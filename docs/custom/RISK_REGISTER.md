# Risk register

Ratings combine likelihood and impact for the proposed personal workflow. All entries are open until their controls have test evidence.

| ID | Risk and rating | Control and gate | Owner |
|---|---|---|---|
| K1 | Current-universe and revised filings bias · Critical | Require historic membership including delistings, filing availability and revision lineage. Block historical performance claims until demonstrated. | Research and data |
| K2 | Unsupported rankings due to missing, stale, drifted or plan-limited data · Critical | Validate provider response and coverage contracts. Record source conflicts and staleness. Test failure at critical gate. | Data |
| K3 | Incorrect valuation, distribution or FX due to mixed periods, units, adjustments, share basis or currency · High | Use period/FX-aware normalization, golden reconciliations, and review material disagreements before publication. | Research |
| K4 | Overfit factors and theme narratives · High | Pre-register outcomes, use walk-forward and one untouched final holdout, report trials and base rates, and require sourced negative evidence. | Research |
| K5 | Understated small-cap and REIT risks · High | Model liquidity, spreads, capacity, debt maturity, refinancing and downside stress. Mark scenarios unassessable if key inputs are missing. | Research |
| K6 | Rights violation through caching, training, Git or reports · High | Maintain approvals by dataset and use. Default to synthetic tests and metadata-only exports where rights are unclear. | Owner and data |
| K7 | Credentials or holdings exposed via logs, fixtures, archives, agent context or Git · Critical | Isolate local state, redact transport errors, scan staged artifacts, test export allowlist and review before sharing. Follow upstream incident and rotation policy. | Security and owner |
| K8 | Instructions embedded in external evidence or unexpected outbound destination · High | Validate and bound inputs, use read-only scoped tools, restrict egress including redirects, and keep data unable to modify configuration or invoke commands. | Agent engineering |
| K9 | Unintended execution or interpretation of research as an order · Critical | No order adapter, broker write credential or tool. Require human review for trade decisions. Test denied operations. | Architecture and owner |
| K10 | Upstream merge, Python or package drift · High | Keep changes namespaced, preserve contracts, test standalone packaging and replay after merge. Preserve notice and maintain a clean upstream comparison. | Maintainer |
| K11 | Provider outage, throttle or quota costs · Medium-high | Per-provider budgets, bounded retries, explicit stale/partial output, no silent substitution. | Data |
| K12 | Crypto/ETF exposure inaccurately treated as equity · High | Separate models and valuation conventions. Disclose ETF overlap, derivatives, dated holdings and crypto quote/venue concentration. | Research |
| K13 | False confidence from large unit-test counts · High | Track financial review, provenance, E2E and empirical validation independently. Report skipped or blocked checks. | QA and research |

Release blockers include K1 for historical claims, K2/K3 for rankings with invalid critical inputs, K6 for live provider use, and K7–K9 for user-held data and agent workflows. Document scope-specific acceptance and residual risk before activating the affected workflow.
