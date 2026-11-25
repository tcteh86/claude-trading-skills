# Development roadmap

The fork now supports Codex discovery, offline workflow replay and a multibagger screener for supplied company snapshots. The phase estimates below come from the original audit. Live provider integration and historical investment-performance validation remain open milestones. [Codex compatibility](CODEX_COMPATIBILITY.md) · [Multibagger discovery](MULTIBAGGER_DISCOVERY.md)

P0 enables the first usable vertical slice. P1 expands research and portfolio support. P2 extends asset coverage. Estimates are focused engineering weeks for one engineer. Data contracts, procurement, and an empirical observation horizon can extend calendar time independently.

| Phase | Priority and estimate | Dependencies | Independently testable acceptance |
|---|---|---|---|
| 0. Audit and planning | P0 · complete with this review | Baseline checkout | Eight planning documents delivered. Upstream source, fixtures, locks, metadata and docs preserved. |
| 1. Evidence foundation | P0 · 2–3 weeks, medium | 0 | Fixture-only provider ports, schema and one reproducible run manifest. Invalid units, conflicting FX, future revisions and incomplete core evidence fail closed. Codex and CLI invoke the same offline path. |
| 2. US valuation and growth screening | P0 · 3–5 weeks, high | 1 and verified US data terms | Adapter parity for legacy script fixtures. Offline screen and dossier include exclusions, valuation scenarios and independent decision dimensions. Approved small live sample reconciles price and filing data. Historical claims remain gated by Phase 3. |
| 3. Historical research and multibaggers | P1 · 4–7 weeks, high | 2 and licensed point-in-time data | Pre-registered cohort/outcomes and evaluation plan. Replay includes delisted securities and dated filings, with cutoff, costs, liquidity, holdout, benchmark and uncertainty checks. Store repeatable results. Retain research-only status where data is insufficient. |
| 4. Themes and ETF evidence | P1/P2 · 3–5 weeks, high | 1, plus 2 for issuer valuations | Config edits change theme definitions without code changes. Two fixture themes show signed direct/indirect links, negative evidence, stale holdings handling and no double counting. An ETF dossier verifies holdings date, fees, concentration and benchmark. |
| 5. SGX equity and REIT income research | P1 · 4–7 weeks, high | 1, 2 methodology, approved SGX feeds | Reconcile representative SGX corporate actions and REIT distributions to issuer records. Verify yield, DPU, leverage and debt stress cases. Suppress unsupported listing or coverage claims. |
| 6. Portfolio risk and human exits | P1 · 3–5 weeks, high | 1 and required asset adapters. US can begin after 2 | Synthetic multi-currency holdings reconcile with cash and corporate actions. Stress and concentration reports show partial coverage. A human confirms exit criteria. No paths submit orders or export private holdings. |
| 7. Crypto module | P2 · 2–4 weeks, medium-high | 1 and approved crypto datasets | Replay a crypto-only universe on a UTC 24/7 calendar. Separate venue liquidity, stablecoin/quote and supply risks. Missing/unsupported markets remain blocked. |

Recommended sequence is 1 → 2 → 3, then 4 and 5 as source access allows. Start portfolio testing with US fixture holdings while SGX rights are investigated. Add crypto after the equity data contracts stabilize. The P0 slice is approximately 5–8 engineering weeks after review. The full scope is approximately 21–36 engineering weeks excluding access negotiations and observation periods.

At each phase, review differences against the upstream baseline, rerun the affected upstream suites, link evidence to each acceptance criterion, and mark any unresolved dependency explicitly. Release only the workflows whose data and method gates passed.
