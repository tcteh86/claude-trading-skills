# Multibagger discovery screener

This Codex skill ranks a declared cohort of listed operating companies on commercial traction, business quality, current valuation and modeled upside. It produces a research watchlist. All examples use fictional listings and the default thresholds are research judgments. Neither nominal share price nor social-media activity contributes a factor. Price momentum has a default weight of 5%. No historical return validation has been performed.

## Run from Codex

In a trusted checkout, install the locked dependencies and open Codex at the repository root. Ask “Use $multibagger-discovery-screener on the synthetic snapshot. Explain why XFIX qualifies and YFIX is speculative.” For real research supply the cutoff, universe, source archive and filters. Codex can gather permitted primary records where tools and data rights allow. The Python screen executes entirely from local inputs. It needs no API key, paid service or broker connection.

```sh
uv sync --locked --no-install-project --extra dev --extra ci
uv run --no-sync python -m investment_intelligence skill multibagger-discovery-screener --input examples/custom/multibagger/synthetic.json
uv run --no-sync python -m pytest -q tests/custom/test_multibagger.py
```

For a retained report, redirect standard output to a private JSON file. On the managed cloud environment use the configured writable uv cache, or replace `uv run` with `uv --no-cache run`. Example with private inputs and an optional policy file follows.

```sh
uv run --no-sync python -m investment_intelligence skill multibagger-discovery-screener --input ../research/cutoff.json --evidence-dir ../research/archive --config ../research/policy.json > ../research/watchlist.json
```

The fixture has three listings as of March 31, 2025. XFIX ranks first. YFIX earns the same attractiveness score but has a severe refinancing finding. ZFIX has unverified accounts. Compare the cutoff, canonical JSON input and configuration digests, resolved settings, calculation-file hashes (UTF-8 with normalized newlines), growth calculator version and source revisions when replaying. Invalid JSON or an invalid policy exits with code 2 on the skill CLI. A valid evaluation with inadequate evidence produces a JSON status of `INSUFFICIENT_DATA`.

## Select the universe and policy

Use one currency per run, including the price, accounts, volume by value and market-size estimates. Defaults select capitalizations of 300 million to 10 billion in USD, 60-session average daily traded value of at least 500,000 and a five-year ranking horizon. Empty exchange, country and sector lists accept all reported values. Filters are exact matches. To include established growth companies, raise the upper limit. The selected horizon controls ranking and each report still includes all three horizons. Partial JSON overrides merge into the [default configuration](../../investment_intelligence/multibagger/defaults.json).

```json
{
  "universe": {
    "exchanges": ["XNAS", "XNYS"],
    "countries": ["US"],
    "sectors": ["Industrial technology"],
    "currency": "USD",
    "min_cap": 300000000,
    "max_cap": 50000000000,
    "min_daily_value": 1000000,
    "horizon_years": 3
  }
}
```

For Singapore use the reporting and quote currency appropriate to the cohort, for example SGD, and the exchange MIC, for example XSES. Cross-currency issuers need reconciled evidence in the reporting currency of the run. P/E and operating cash flow assume ordinary operating companies. Banks, REITs, funds and tokens require different valuation methods. The cohort is supplied by the researcher. A user-selected shortlist gives a ranking within that shortlist only.

## Build the evidence snapshot

The [synthetic snapshot](../../examples/custom/multibagger/synthetic.json) contains a complete copyable structure. Set `schema_version` to 1, `dataset` to `research` for actual research, and `mode` to `snapshot` or `historical`. Supply a timezone-aware `as_of` on the roster’s market session date. The universe contains `source_id` and unique listing IDs (`MIC:TICKER`) in `members`. Provide one company row for every member, including members with missing evidence. Specify the exact source roster in that same order.

Each company has an `id` and `sections`. Every section contains `data`, a list of source IDs in `sources`, a timezone-aware `prepared_at` and `review`. Mark the latter `verified` only after checking the source and reconciling conflicts. An absent field, null value, stale source, unsupported claim or unresolved review makes that assessment unavailable. Use zero only for a documented zero.

| Section | Inputs and interpretation |
|---|---|
| `profile` | Company name, ticker, instrument type (the supported model uses `listed_operating_equity`), headquarters, exchange, country, sector, products/services, customers, competitors and investment theme. Describe direct or indirect revenue exposure. |
| `market` | Currency, `base_units`, share price, current shares outstanding and 60-session average daily traded value. Use contemporaneous exchange or regulator data for one consistent share class. |
| `accounts` | Two comparable reported consolidated trailing years, 350–380 days apart. Supply both fiscal ends, revenue, net income attributable to common holders and weighted-average diluted shares for both periods. Current inputs include operating cash flow, positive capex outflow, share-based compensation, total debt and unrestricted cash. Use reported figures with a consistent share and currency basis. Set `basis` to `reported_consolidated_ttm`. |
| `exposures` | Currency and base units, debt principal due within 12 months, potential dilution as a percentage of outstanding shares, and revenue share of the largest customer. Include convertibles, warrants, options and committed issuance on a consistent basis. |
| `risk_review` | Supply a specific filing, exchange or regulator finding and severity for each of going concern/bankruptcy, refinancing, regulation, delisting, reverse splits, related-party transactions and accounting irregularities. Document the searched period and schedule for a clear assessment. A missing disclosure is unknown. |
| `industry` | Industry growth in percent, total addressable market and realistically obtainable **annual revenue** for the issuer, all monetary values in the run currency and base units. Explain the serviceable geography, customers, capacity and obtainable share in the cited assessment. |
| `commercial` | Currency, base units, strongest verified stage, matching fiscal period end and attributable revenue recognized during the TTM. Follow an announcement or MOU to a signed agreement, paid deployment or actual filing. A contract value or backlog is distinct from recognized revenue. |
| `moat`, `management` | Each needs a 0–4 assessment and a specific rationale. Use 0 for verified failure or absence of an advantage, 1 for weak/fragile evidence of execution, 2 for a demonstrated but replicable position, 3 for repeatable execution or defensible advantage, and 4 for sustained performance against competitors or prior milestones. Missing evidence stays unknown. |
| `institutional` | Comparable current and previous reporting populations and ownership change in percentage points, using publication dates and adjusting for corporate actions. Upstream A-grade coverage is required for the factor. |
| `technical` | Dated, split-adjusted open/high/low/close observations from the exchange. Include five consecutive recent completed weeks. Use only adjustment events known by the cutoff. |
| `assumptions` | Bear, base and bull cases, each with a rationale in `basis` and ordered [low, high] bounds for annual revenue growth, terminal net margin, annual share dilution (all percentages) and terminal P/E. Vary at least one driver per case. Optional `by_horizon` entries keyed by `"1"`, `"3"` or `"5"` override individual drivers and require a horizon-specific `basis`. The sample varies first-year base margins to reflect commissioning costs. Cite the primary observations anchoring these analyst assumptions. |
| `thesis` | Bull case, bear case, catalysts, explicit thesis invalidation and measurable monitoring metrics. Keep forecasts visibly conditional. |

Sources are keyed by ID. Record `kind`, `listing`, public credential-free `uri`, document `revision`, precise `locator`, `verified_by`, `observed_at`, `published_at`, `retrieved_at` and a `supports` array such as `["accounts.revenue","accounts.prior_revenue"]`. Use the fiscal period end or market observation for the observation time and the release time of that specific revision for publication. Sources must be published by section preparation and the cutoff. Retrieval records when the archived revision was accessed and may be later for a historical replay. Default maximum ages are seven days for market quotes, 210 days for risk reviews and exposures, and 460 days for other filing and research sections. Filing-based financials and exchange-based prices have narrower accepted source kinds than business descriptions. Retain original documents and extraction notes privately under their applicable terms.

For **research** sources also supply `document` (relative UTF-8 extract path inside the archive), its SHA-256 in `sha256`, and a literal nonempty `excerpt` from the archived primary text. Store each reviewed extract as a UTF-8 JSON object with a `source` header matching its listing, kind, URI, revision, locator, observation and publication times. Include `text` containing verbatim primary material and `claims` mapping supported field names to their reviewed, normalized values. The reader checks both the excerpt and the exact values before using the claims. For example, a fictional filing extract for an issuer reporting in USD could have this form.

```json
{
  "source": {
    "listing": "XNAS:XFIX", "kind": "filing",
    "uri": "https://filings.example.invalid/fictional-annual-report",
    "revision": "v1", "locator": "Consolidated income statement, p. 41",
    "observed_at": "2024-12-31T23:59:59Z", "published_at": "2025-02-20T16:30:00Z"
  },
  "text": "Revenue for the trailing twelve months was $400 million.",
  "claims": {"accounts.revenue": 400000000, "accounts.currency": "USD"}
}
```

Record the digest of the exact bytes after review. Use `python -c "import hashlib, pathlib, sys; print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())" ../research/archive/filing.json`. For the exchange/regulator source with listing `UNIVERSE`, archive a JSON roster with its matching `source` header, primary `text` and the same `members`, `observed_at`, `point_in_time` and, when declared, `includes_later_delisted` as the source metadata. The roster must cover the cutoff date. These checks detect missing, changed or mismatched archived material. The reviewer is responsible for document authenticity, extraction accuracy, rights, reporting basis and the interpretation of each claim. Synthetic fixtures may use `fixture://` citations and require no archive.

## Read the scores and cases

| Factor | Default weight | Calculation |
|---|---:|---|
| Addressable market and industry growth | 15% | Lesser of normalized industry growth and obtainable annual revenue relative to twice current revenue. |
| Revenue and earnings growth | 15% | Mean normalized reported revenue and diluted EPS growth across comparable trailing periods. |
| Competitive moat and technology | 15% | Reviewed moat rating × 25. |
| Financial health and free cash flow | 15% | Mean normalized FCF margin and cash/debt coverage. |
| Valuation attractiveness | 15% | Normalized lower base-case annualized price return at the selected horizon. |
| Customer adoption and partnerships | 10% | Announcement 5, MOU 10, pilot 25, binding contract 50, commercial deployment 70. Filing-supported recognized revenue earns 70–100 according to its share of reported TTM sales. |
| Management and execution | 5% | Reviewed execution rating × 25. |
| Institutional ownership trends | 5% | 50 plus 10 × percentage-point change, with adequate holder coverage. |
| Technical momentum | 5% | 50 plus twice the four-week percentage price change from completed weeks. |

All factors are capped at 0–100. Weights must sum to 100. Attractiveness is the verified weighted sum. Its range shows what is still unresolved without redistributing the missing weight. Evidence confidence is the mean of weighted factor coverage, mandatory risk-check coverage and completed profile/thesis coverage. It measures input completeness and qualification. Investment outcome probabilities would require a separately validated model.

Risk has its own 0–100 score, the mean of worst and average check severity. Clear/elevated/severe map to 0/50/100. A missing mandatory check yields `UNKNOWN` severity and a null risk score. Every severe finding or aggregate score at or above the configured ceiling is speculative. Numerical checks cover trailing FCF cash-burn runway, cash against one-year principal maturities, historical diluted-share growth, potential issuance, SBC/revenue, customer concentration and average traded value. For upper risk limits, 70% of the limit is elevated and the limit is severe. For minimum coverage/runway/liquidity, below the limit is elevated and at or below half is severe. Nonnegative trailing FCF is identified as no trailing burn. Refinancing facilities and forward cash needs still need separate review.

The calculation enumerates the extreme combinations of growth, margins, dilution and terminal P/E over 1, 3 and 5 years. Revenue and shares compound from the cutoff. Terminal income equals revenue times net margin. Terminal EPS times P/E gives a price range. Returns measure per-share price change and exclude dividends, transaction costs, FX and taxes. A nonpositive earnings endpoint makes a P/E range unavailable. The inverse calculation sets the target price to 2, 5 or 10 times current price. At base-case future shares, required equity value equals target price times future shares. Divide by terminal P/E for required profit and by net margin for required revenue. The output also shows required revenue growth, required margin at modeled revenue and required P/E at modeled income. These are conditional hurdles with no assigned probabilities.

Only records with all seven core factors, complete mandatory risk evidence, a sourced thesis and commercial traction at least at binding-contract stage can rank. The selected horizon requires a modeled bear loss, ordered low and high scenario endpoints, a positive lower base return and a supported obtainable market covering both the lower base and lower bull revenue estimates. The ratio of upside at the lower bull endpoint to loss at the lower bear endpoint must reach 1.25 by default. Defaults require attractiveness of at least 55 and confidence of at least 80. The watchlist sorts by attractiveness, confidence and listing ID. Inspect `speculative`, `excluded`, `insufficient_data`, each row's `blockers` and `issues`, and the run's `universe_blockers` alongside the ranking.

## Historical evaluation and upstream reuse

Freeze every historical roster at the decision cutoff, including companies that subsequently failed, merged or delisted. Require archival coverage of those listings and retain dated versions of each filing, ownership report, price adjustment and thesis. Current membership, revised earnings, hindsight-selected themes and later-prepared assumptions cannot substitute for contemporaneous inputs. Historical mode suppresses the ranking if a roster member is absent or incomplete evidence could induce selection on availability. Snapshot mode reports incomplete companies separately. This is a point-in-time screen. Realized return testing would also need delisting proceeds, corporate actions, tradable lags and costs, a frozen policy, walk-forward evaluation and an untouched holdout.

The financial adapter calls the upstream growth screener for reported FCF reconciliation, margins, yields, diluted-share growth, EPS and revenue growth, and per-share scenarios. Institutional grades, completed weekly bars and document unit/date checks also run upstream code. The Codex instructions use the stock-analysis business framework, theme-detector's cross-sector beneficiary analysis, and scenario-analyzer's event playbooks when constructing the dossier. The fork adds the evidence gates, separate risk policy, cross-horizon ranges and inverse return hurdles. [Upstream adapter](../../investment_intelligence/multibagger/upstream.py) · [Codex research steps](../../.agents/skills/multibagger-discovery-screener/SKILL.md)

## Verification

On Linux with Python 3.13.5, Codex listed the repository skill as enabled and two offline CLI runs produced byte-identical reports. The fork suite passed all 74 tests, including 61 screener tests. The seven referenced upstream skill suites passed 1,577 tests in isolated runs, with two skips. The full upstream suite matched its baseline of 17,606 passes, three skips and one failure in theme-detector's missing-calendar test. That test passed when run alone. Lint, formatting, catalog validation and the offline secret scan passed. Native Windows and macOS execution and live issuer research await verification.
