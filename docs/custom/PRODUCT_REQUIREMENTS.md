# Product requirements

Build a personal research assistant that converts reproducible data and attributable evidence into watchlists, valuation dossiers, and portfolio review notes. The user approves assumptions and investment decisions. The product has no automatic order submission, broker write access, or guaranteed-return claims.

## Research workflows

| ID | Priority | User outcome | Acceptance |
|---|---|---|---|
| R1 | P0 | Discover undervalued US small/mid-cap growth stocks. | A dated, versioned screen reports eligible, evaluated, excluded and blocked counts. Each ranked candidate has growth quality, valuation range, liquidity, risk, and evidence. The user can narrow market-cap, liquidity, and sector filters. |
| R2 | P1 | Discover early multibagger candidates. | Generate a watchlist from durable growth, reinvestment, market opportunity, competitive position, dilution, and financing runway. Define the outcome horizon and total-return multiple before evaluation. Report base rates, downside and failed cases alongside successes. |
| R3 | P1 | Identify emerging themes and beneficiaries. | Show time-stamped signals and evidence for both direct revenue exposure and indirect supplier/customer relationships. Distinguish reported revenue from qualitative inference. Show conflicting evidence and ETF overlap. |
| R4 | P1 | Discover sustainable dividends and SGX REIT distributions. | Report recurring versus special distributions, payout coverage, debt/refinancing, and a stress case. Reconcile SGX REIT DPU and distributable income with source periods and currency. Missing material inputs block a sustainability verdict. |
| R5 | P0 | Assess valuation of a single stock today or as of a historical date. | Provide a dated price, explicit scenarios, comparable metrics where valid, sensitivity, equity-to-enterprise bridge where appropriate, and reasons the thesis could fail. Stale or conflicting critical data blocks a current conclusion. |
| R6 | P1 | Review portfolio risk, discipline and exits. | Import a local synthetic or user-held snapshot, reconcile cash and positions, show concentrations and FX exposure, and produce human-reviewed thesis, risk and exit triggers. Missing positions or stale marks qualify or block totals. |
| R7 | P2 | Compare ETFs and research crypto separately. | ETF outputs cover fees, concentration, exposures, index methodology and fund trading. Crypto outputs use a separate asset identity, benchmark, liquidity, venue, supply/unlock and drawdown methodology. Cross-asset aggregation is limited to portfolio exposure and risk with explicit valuation timestamps and FX. |

## Product rules

- Seed a user-editable taxonomy with physical AI, humanoid robotics, semiconductor equipment, edge AI, IoT, AI data centre infrastructure, satellite communications, energy storage, automation and cybersecurity. Version definitions, synonyms, value-chain roles and effective dates. Allow themes to change without code changes.
- Report attractiveness, risk, and evidence confidence as separate outputs, with versioned definitions. Use `research_only` for incomplete evidence that supports a lead and `blocked` when required inputs prevent a decision. Rank only eligible candidates in comparable cohorts. Report the supported scope of every result.
- Attach field-level evidence with source, available time, observation time, currency and unit. Show price age, financial period, adjustment conventions, assumptions, and coverage. Unknown values remain unknown. A source conflict needs resolution or an explicit block.
- Support offline replay with synthetic or rights-cleared inputs. Live access must be explicitly enabled and limited to permitted data. Keep user-owned records private and export only selected redacted research artifacts.
- Judge research quality on reproducibility, data coverage, decision usefulness, and evaluation against stated benchmarks. Neither a score nor a backtest establishes future returns.

## Launch scope

Start with US equity screening and one single-stock dossier. Extend to themes, portfolio workflows, and SGX as evidence and entitlements permit. A local CLI and Codex entry point are sufficient for the first release. Hosted services, order execution, automated tax advice, and real-time trading are outside the planned scope.
