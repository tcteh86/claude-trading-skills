"""Screen the declared listing cohort as of one research cutoff."""

from datetime import date
from statistics import mean

from . import upstream
from .contracts import (
    ACCOUNTS,
    CASES,
    FLAGS,
    PRIMARY,
    PROFILE,
    STAGES,
    THESIS,
    Evidence,
    number,
    text,
    timestamp,
)
from .valuation import assumptions, projections

MARKET = ("currency", "units", "price", "shares_outstanding", "avg_daily_value_60d")
EXPOSURES = ("debt_due_12m", "potential_dilution_pct", "largest_customer_revenue_pct")
LEVEL = {"clear": 0, "elevated": 50, "severe": 100}
UNKNOWN = "UNKNOWN"


def strings(data):
    if not all(text(v) for v in data.values()):
        raise ValueError("expected nonempty sourced descriptions")
    return data


def money(data, currency):
    if data["currency"] != currency or data["units"] != "base_units":
        raise ValueError("currency or units need reconciliation")


def financials(data, currency, cutoff, max_age):
    money(data, currency)
    end = date.fromisoformat(data["fiscal_end"])
    prior = date.fromisoformat(data["prior_fiscal_end"])
    if data["basis"] != "reported_consolidated_ttm" or (cutoff.date() - end).days > max_age:
        raise ValueError("stale or non-reported financial performance")
    if end > cutoff.date() or not 350 <= (end - prior).days <= 380:
        raise ValueError("expected two comparable trailing years available at the cutoff")
    for field in set(ACCOUNTS) - {"basis", "currency", "units", "fiscal_end", "prior_fiscal_end"}:
        number(data[field])
    for k in ("revenue", "prior_revenue", "diluted_shares", "prior_diluted_shares"):
        if data[k] <= 0:
            raise ValueError(f"{k} must be positive")
    for k in ("unrestricted_cash", "debt", "sbc", "capex"):
        number(data[k], 0)
    return data


def grade(value, target):
    return max(0, min(100, 100 * value / target))


def risk_analysis(accounts, market_data, metrics, exposures, flags, thresholds):
    risks = {}

    def assess(name, observed, severity, criterion):
        risks[name] = {"value": observed, "severity": severity, "criterion": criterion}

    def threshold(name, value, limit, *, lower=False):
        if value is None:
            severity = UNKNOWN
        else:
            ratio = value / limit
            if lower:
                severity = "severe" if ratio <= 0.5 else "elevated" if ratio < 1 else "clear"
            else:
                severity = "severe" if ratio >= 1 else "elevated" if ratio >= 0.7 else "clear"
        assess(
            name,
            value,
            severity,
            {"threshold": limit, "risk_increases": "below" if lower else "above"},
        )

    for key in FLAGS:
        review = flags.get(key, {})
        assess(key, review.get("finding"), review.get("severity", UNKNOWN), "primary-source review")
    fcf = metrics.get("standard_fcf")
    if fcf is not None and fcf >= 0:
        assess("cash_runway", None, "clear", "No net cash burn on trailing FCF basis")
    else:
        months = 12 * accounts["unrestricted_cash"] / abs(fcf) if fcf is not None else None
        threshold("cash_runway", months, thresholds["runway_months"], lower=True)
    due = exposures.get("debt_due_12m")
    if due == 0:
        assess("debt_maturity", 0, "clear", "No principal due in next 12 months")
    else:
        coverage = accounts["unrestricted_cash"] / due if accounts and due is not None else None
        threshold("debt_maturity", coverage, thresholds["debt_cash_coverage"], lower=True)
    threshold(
        "historical_dilution",
        metrics.get("diluted_share_cagr_pct"),
        thresholds["historical_dilution_pct"],
    )
    threshold(
        "potential_dilution",
        exposures.get("potential_dilution_pct"),
        thresholds["potential_dilution_pct"],
    )
    threshold(
        "share_based_compensation", metrics.get("sbc_revenue_pct"), thresholds["sbc_revenue_pct"]
    )
    threshold(
        "customer_concentration",
        exposures.get("largest_customer_revenue_pct"),
        thresholds["customer_concentration_pct"],
    )
    threshold(
        "liquidity",
        market_data.get("avg_daily_value_60d"),
        thresholds["risk_daily_value"],
        lower=True,
    )
    levels = [r["severity"] for r in risks.values()]
    known = [LEVEL[level] for level in levels if level in LEVEL]
    risk_score = round((max(known) + mean(known)) / 2, 2) if len(known) == len(levels) else None
    classification = (
        "SPECULATIVE"
        if "severe" in levels
        or (risk_score is not None and risk_score >= thresholds["speculative_risk_score"])
        else UNKNOWN
        if UNKNOWN in levels
        else "ELEVATED"
        if "elevated" in levels
        else "STANDARD"
    )
    return {"classification": classification, "score": risk_score, "checks": risks}


def weekly_momentum(data, cutoff):
    bars = data["bars"]
    if not isinstance(bars, list) or data["adjustment"] != "split_adjusted":
        raise ValueError("need split-adjusted OHLC bars")
    for bar in bars:
        if date.fromisoformat(bar["date"]) > cutoff.date():
            raise ValueError("future price bar")
        for item in ("open", "high", "low", "close"):
            if number(bar[item]) <= 0:
                raise ValueError("nonpositive bar")
        if (
            not bar["low"]
            <= min(bar["open"], bar["close"])
            <= max(bar["open"], bar["close"])
            <= bar["high"]
        ):
            raise ValueError("inconsistent OHLC bar")
    series = upstream.technical.build_sorted_daily_series(bars)
    if len(series) != len(bars):
        raise ValueError("duplicate or incomplete price bars")
    weeks = upstream.technical.resample_weekly(series, cutoff.date().isoformat())[-5:]
    if (
        len(weeks) != 5
        or (date.fromisoformat(weeks[-1]["week_of"]) - date.fromisoformat(weeks[0]["week_of"])).days
        != 28
        or (cutoff.date() - date.fromisoformat(weeks[-1]["week_of"])).days > 14
    ):
        raise ValueError("need five consecutive recent completed weeks")
    change = upstream.percent(weeks[-1]["close"] - weeks[0]["close"], weeks[0]["close"])
    return {"four_week_return_pct": change, "completed_week": weeks[-1]["week_of"]}


def scenario_support(cases, sector):
    upside_downside = None
    hurdle_warnings = []
    if cases:
        base = cases["base"]
        bear_returns, bull_returns = cases["bear"]["upside_pct"], cases["bull"]["upside_pct"]
        if bear_returns and bull_returns and base.get("upside_pct"):
            if bear_returns[0] >= 0:
                hurdle_warnings.append("bear case does not model a loss")
            elif any(
                not bear_returns[i] <= base["upside_pct"][i] <= bull_returns[i] for i in (0, 1)
            ):
                hurdle_warnings.append("scenario ordering is inconsistent")
            else:
                upside_downside = max(0, bull_returns[0]) / abs(bear_returns[0])
        if sector and base["revenue"][0] > sector["obtainable_market"]:
            hurdle_warnings.append(
                "even the lower base revenue exceeds the estimated obtainable market"
            )
        elif sector and cases["bull"]["revenue"][0] > sector["obtainable_market"]:
            hurdle_warnings.append(
                "even the lower bull revenue exceeds the estimated obtainable market"
            )
    return upside_downside, hurdle_warnings


def factor_scores(
    accounts, metrics, sector, moat, management, adoption, base, flow, technical, thresholds
):
    eps_growth = metrics.get("gaap_eps_cagr_pct")
    adoption_score = None
    if adoption:
        if adoption["stage"] != "recognized_revenue":
            adoption_score = STAGES[adoption["stage"]]
        elif accounts:
            adoption_score = 70 + 0.3 * grade(
                adoption["recognized_share_of_ttm_revenue_pct"],
                thresholds["adoption_revenue_target_pct"],
            )
    return {
        "industry": min(
            grade(sector["industry_growth_pct"], thresholds["industry_growth_target_pct"]),
            grade(sector["obtainable_market"] / accounts["revenue"], 2),
        )
        if sector and accounts
        else None,
        "growth": mean(
            [
                grade(metrics["revenue_cagr_pct"], thresholds["revenue_growth_target_pct"]),
                grade(eps_growth, thresholds["eps_growth_target_pct"]),
            ]
        )
        if metrics and eps_growth is not None
        else None,
        "moat": 25 * moat["rating"] if moat else None,
        "financial_health": mean(
            [
                grade(metrics["fcf_margin_pct"], thresholds["fcf_margin_target_pct"]),
                100
                if accounts["debt"] == 0
                else grade(accounts["unrestricted_cash"] / accounts["debt"], 1),
            ]
        )
        if metrics
        else None,
        "valuation": grade(base["cagr_pct"][0], thresholds["return_target_pct"])
        if base.get("cagr_pct")
        else None,
        "adoption": adoption_score,
        "management": 25 * management["rating"] if management else None,
        "institutional": max(0, min(100, 50 + 10 * flow["ownership_change_pp"]))
        if flow and flow["coverage_grade"] == "A"
        else None,
        "momentum": max(0, min(100, 50 + 2 * technical["four_week_return_pct"]))
        if technical
        else None,
    }


def screen_company(row, evidence, settings):
    issues = {}
    accepted = {}  # Per-field verified source IDs, grouped by assessment.

    def read(section, fields, kinds=PRIMARY, validate=lambda v: v, label=None):
        key = label or section
        try:
            values, cited = evidence.section(row, section, fields, kinds)
            data = validate(values)
        except (KeyError, TypeError, ValueError) as exc:
            issues[key] = str(exc)
            return {}
        accepted[key] = cited
        return data

    universe, thresholds, weights = (
        settings["universe"],
        settings["thresholds"],
        settings["weights"],
    )
    profile = read("profile", PROFILE, validate=strings)
    if profile and row["id"] != f"{profile['exchange']}:{profile['ticker']}":
        issues["profile"] = "listing ID does not match exchange and ticker"
        accepted.pop("profile")
        profile = {}

    def market(data):
        money(data, universe["currency"])
        for k in MARKET[2:]:
            number(data[k], 0)
        if not data["price"] or not data["shares_outstanding"]:
            raise ValueError("price and outstanding shares must be positive")
        return data

    market_data = read("market", MARKET, {"exchange", "regulator"}, market)
    cap = market_data["price"] * market_data["shares_outstanding"] if market_data else None
    exclusions = []
    if profile and profile["instrument_type"] != "listed_operating_equity":
        exclusions.append("unsupported instrument type for operating-company valuation")
    for key, field in (("countries", "country"), ("exchanges", "exchange"), ("sectors", "sector")):
        if profile and universe[key] and profile[field] not in universe[key]:
            exclusions.append(field)
    if market_data and not universe["min_cap"] <= cap <= universe["max_cap"]:
        exclusions.append("market_cap")
    if market_data and market_data["avg_daily_value_60d"] < universe["min_daily_value"]:
        exclusions.append("liquidity")
    accounts = read(
        "accounts",
        ACCOUNTS,
        {"filing", "regulator"},
        lambda data: financials(
            data, universe["currency"], evidence.cutoff, thresholds["max_report_age_days"]
        ),
    )
    if accounts:
        for claim, refs in accepted["accounts"].items():
            period = "prior_fiscal_end" if claim.startswith("accounts.prior_") else "fiscal_end"
            period_end = date.fromisoformat(accounts[period])
            valid_refs = [
                sid
                for sid in refs
                if timestamp(evidence.sources[sid]["observed_at"]).date() >= period_end
            ]
            if not valid_refs:
                issues["accounts"] = f"{claim}: filing evidence predates the fiscal period"
                accepted.pop("accounts")
                accounts = {}
                break
            accepted["accounts"][claim] = valid_refs
    metrics = {}
    if accounts and market_data:
        cash_flow_refs = sorted(
            set(accepted["accounts"]["accounts.ocf"] + accepted["accounts"]["accounts.capex"])
        )
        try:
            metrics = upstream.accounts(accounts, cap, cash_flow_refs)
        except ValueError as exc:
            issues["accounts"] = str(exc)
            accepted.pop("accounts")
            accounts = {}

    def exposure(data):
        money(data, universe["currency"])
        for k in EXPOSURES:
            number(data[k], 0, 100 if k == "largest_customer_revenue_pct" else None)
        if accounts and data["debt_due_12m"] > accounts["debt"]:
            raise ValueError("maturing debt exceeds total debt")
        return data

    exposures = read(
        "exposures", (*EXPOSURES, "currency", "units"), {"filing", "regulator"}, exposure
    )
    flags = {}
    for key in FLAGS:
        item = read("risk_review", [key], {"filing", "regulator", "exchange"}, label=key)
        if (
            item
            and isinstance(item[key], dict)
            and isinstance(item[key].get("severity"), str)
            and item[key]["severity"] in LEVEL
            and text(item[key].get("finding"))
        ):
            flags.update(item)
        elif item:
            accepted.pop(key)
            issues[key] = "unrecognized risk review"
    risk = risk_analysis(accounts, market_data, metrics, exposures, flags, thresholds)

    def industry(data):
        number(data["industry_growth_pct"])
        number(data["tam"], 0)
        number(data["obtainable_market"], 0, data["tam"])
        money(data, universe["currency"])
        if not data["obtainable_market"]:
            raise ValueError("obtainable market needs a positive supported estimate")
        return data

    sector = read(
        "industry",
        ["industry_growth_pct", "tam", "obtainable_market", "currency", "units"],
        validate=industry,
    )

    def commercial(data):
        money(data, universe["currency"])
        if date.fromisoformat(data["fiscal_end"]) > evidence.cutoff.date():
            raise ValueError("commercial revenue period after cutoff")
        if accounts and data["fiscal_end"] != accounts["fiscal_end"]:
            raise ValueError("commercial and financial revenue periods differ")
        if data["stage"] not in STAGES:
            raise ValueError("unknown commercial stage")
        number(data["recognized_revenue"], 0, accounts["revenue"] if accounts else None)
        if (data["stage"] == "recognized_revenue") != (data["recognized_revenue"] > 0):
            raise ValueError("stage disagrees with recognized revenue")
        return data

    adoption = read(
        "commercial",
        ["stage", "recognized_revenue", "currency", "units", "fiscal_end"],
        {"filing", "regulator", "customer", "issuer"},
        commercial,
    )
    if adoption and adoption["recognized_revenue"]:
        revenue_refs = accepted["commercial"]["commercial.recognized_revenue"]
        filed = [
            sid
            for sid in revenue_refs
            if evidence.sources[sid]["kind"] in {"filing", "regulator"}
            and timestamp(evidence.sources[sid]["observed_at"]).date()
            >= date.fromisoformat(adoption["fiscal_end"])
        ]
        if filed:
            accepted["commercial"]["commercial.recognized_revenue"] = filed
        else:
            issues["commercial"] = "recognized revenue requires filing support"
            accepted.pop("commercial")
            adoption = {}
    if adoption:
        adoption["recognized_share_of_ttm_revenue_pct"] = (
            upstream.percent(adoption["recognized_revenue"], accounts["revenue"])
            if accounts
            else None
        )

    def research(data):
        number(data["rating"], 0, 4)
        if not text(data["rationale"]):
            raise ValueError("rating needs a rationale")
        return data

    moat = read("moat", ["rating", "rationale"], validate=research)
    management = read("management", ["rating", "rationale"], validate=research)

    def ownership(data):
        for k in ("holders", "prior_holders"):
            if type(data[k]) is not int or data[k] < 0:
                raise ValueError("invalid institutional holder counts")
        number(data["ownership_change_pp"], -100, 100)
        return dict(
            data,
            coverage_grade=upstream.flow.coverage_grade(data["holders"], data["prior_holders"]),
        )

    flow = read(
        "institutional",
        ["holders", "prior_holders", "ownership_change_pp"],
        {"filing", "regulator"},
        ownership,
    )

    technical = read(
        "technical",
        ["bars", "adjustment"],
        {"exchange"},
        lambda data: weekly_momentum(data, evidence.cutoff),
    )
    thesis = read("thesis", THESIS, validate=strings)
    findings = upstream.quality.run_checks(
        "\n".join([*profile.values(), *thesis.values()]),
        checks=["units", "dates"],
        as_of=evidence.cutoff.date(),
    )
    if any(finding.severity == "ERROR" for finding in findings):
        issues["thesis"] = "data-quality-checker flagged a material inconsistency"
        accepted.pop("thesis", None)
        thesis = {}
    drivers = read("assumptions", CASES, validate=assumptions)
    horizons = (
        projections(accounts, market_data, drivers) if accounts and market_data and drivers else {}
    )
    horizon = str(universe["horizon_years"])
    base = horizons[horizon]["scenarios"]["base"] if horizons else {}
    cases = horizons[horizon]["scenarios"] if horizons else {}
    upside_downside, hurdle_warnings = scenario_support(cases, sector)
    scores = factor_scores(
        accounts, metrics, sector, moat, management, adoption, base, flow, technical, thresholds
    )
    coverage = sum(weights[k] for k, v in scores.items() if v is not None)
    lower_score = sum(weights[k] * v / 100 for k, v in scores.items() if v is not None)
    risk_coverage = mean(v["severity"] != UNKNOWN for v in risk["checks"].values()) * 100
    confidence = round((coverage + risk_coverage + (bool(profile) + bool(thesis)) * 50) / 3, 2)
    blocked = [
        k
        for k in (
            "industry",
            "growth",
            "financial_health",
            "valuation",
            "adoption",
            "moat",
            "management",
        )
        if scores[k] is None
    ]
    if not profile or not thesis or risk["score"] is None:
        blocked.append("incomplete profile, thesis or mandatory risk evidence")
    if not coverage or confidence < thresholds["min_confidence"]:
        blocked.append("below evidence confidence threshold")
    if adoption and adoption["stage"] not in (
        "commercial_deployment",
        "recognized_revenue",
        "binding_contract",
    ):
        blocked.append("commercial traction unverified")
    if upside_downside is None or hurdle_warnings:
        blocked.extend(hurdle_warnings or ["downside or upside cannot be valued"])
    elif upside_downside < thresholds["min_upside_downside"]:
        exclusions.append("insufficient upside relative to modeled downside")
    if base.get("cagr_pct") and base["cagr_pct"][0] <= 0:
        exclusions.append("nonpositive lower base-case return")
    if not exclusions and lower_score < thresholds["min_attractiveness"] and not blocked:
        if lower_score + 100 - coverage >= thresholds["min_attractiveness"]:
            blocked.append("missing evidence spans the attractiveness threshold")
        else:
            exclusions.append("below attractiveness threshold")
    status = (
        "EXCLUDED"
        if exclusions
        else "SPECULATIVE"
        if risk["classification"] == "SPECULATIVE"
        else "INSUFFICIENT_DATA"
        if blocked
        else "ELIGIBLE"
    )
    return {
        "id": row["id"],
        "status": status,
        **profile,
        "thesis": thesis,
        "document_quality": [vars(finding) for finding in findings],
        "factors": scores,
        "attractiveness_score": round(lower_score, 2) if coverage else None,
        "attractiveness_range": [round(lower_score, 2), round(lower_score + 100 - coverage, 2)],
        "financial_risk": risk,
        "evidence_confidence": confidence,
        "evidence_coverage_pct": coverage,
        "current_valuation": {
            "market_cap": cap,
            "price": market_data.get("price"),
            "currency": universe["currency"],
            "trailing_pe": market_data["price"] * accounts["diluted_shares"] / accounts["income"]
            if accounts and market_data and accounts["income"] > 0
            else None,
            "enterprise_value": metrics.get("enterprise_value"),
            "ev_to_fcf": metrics.get("ev_to_fcf"),
        },
        "financial_performance": {"reported": accounts, "derived": metrics},
        "commercial_validation": adoption,
        "market_opportunity": sector,
        "ownership": flow,
        "momentum": technical,
        "moat": moat,
        "management": management,
        "risk_inputs": exposures,
        "market_inputs": market_data,
        "upside_to_downside": upside_downside,
        "valuation_horizons": horizons,
        "exclusions": exclusions,
        "blockers": blocked,
        "issues": issues,
        "source_refs": {
            claim: refs for section in accepted.values() for claim, refs in section.items()
        },
    }


def screen(snapshot, settings, evidence_dir=None):
    if (
        snapshot["schema_version"] != 1
        or snapshot["dataset"] not in ("synthetic", "research")
        or snapshot["mode"] not in ("snapshot", "historical")
    ):
        raise ValueError("unsupported snapshot schema, dataset or mode")
    ev = Evidence(snapshot, settings, evidence_dir)
    universe = snapshot["universe"]
    members = universe["members"]
    if (
        not isinstance(members, list)
        or not all(text(v) for v in members)
        or len(set(members)) != len(members)
    ):
        raise ValueError("expected distinct listing IDs in membership snapshot")
    rows = snapshot["companies"]
    ids = [r["id"] for r in rows]
    if len(set(ids)) != len(ids) or set(ids) - set(members):
        raise ValueError("duplicate listing or listing outside frozen membership")
    sid = universe.get("source_id")
    source = ev.sources.get(sid, {})
    problems = []
    if (
        not ev.verified(sid, "UNIVERSE", "universe.members", {"exchange", "regulator"}, 1, members)
        or source.get("members") != members
    ):
        problems.append("membership does not reconcile to a verified as-of roster")
    if (
        source.get("point_in_time") is not True
        or problems
        or source.get("observed_at") is None
        or timestamp(source["observed_at"]).date() != ev.cutoff.date()
    ):
        problems.append("as-of listing vintage unavailable")
    if snapshot["mode"] == "historical" and source.get("includes_later_delisted") is not True:
        problems.append("historical universe lacks delisted-security coverage")
    if set(members) != set(ids):
        problems.append("missing company records for declared membership")
    report = {
        "schema_version": 1,
        "method_version": "multibagger-1.0",
        "as_of": snapshot["as_of"],
        "dataset": snapshot["dataset"],
        "mode": snapshot["mode"],
        "scope": "declared listing cohort",
        "growth_contract": upstream.growth_version,
        "configuration": settings,
        "membership_source": sid,
        "missing_members": sorted(set(members) - set(ids)),
        "universe_count": len(members),
        "universe_blockers": problems,
        "ranked_watchlist": [],
        "speculative": [],
        "insufficient_data": [],
        "excluded": [],
        "sources": {},
    }
    if problems:
        return dict(report, status="INSUFFICIENT_DATA")
    report["sources"][sid] = ev.citation(sid)
    reviewed = [screen_company(row, ev, settings) for row in sorted(rows, key=lambda r: r["id"])]
    for row in reviewed:
        for refs in row["source_refs"].values():
            for ref in refs:
                report["sources"][ref] = ev.citation(ref)
    for status, key in (
        ("SPECULATIVE", "speculative"),
        ("INSUFFICIENT_DATA", "insufficient_data"),
        ("EXCLUDED", "excluded"),
    ):
        report[key] = [r for r in reviewed if r["status"] == status]
    eligible = [r for r in reviewed if r["status"] == "ELIGIBLE"]
    if snapshot["mode"] == "historical" and any(
        r["blockers"] and not r["exclusions"] for r in reviewed
    ):
        problems.append("incomplete historical evidence would select on data availability")
        return dict(report, status="INSUFFICIENT_DATA", unranked_eligible=eligible)
    eligible.sort(key=lambda r: (-r["attractiveness_score"], -r["evidence_confidence"], r["id"]))
    report["ranked_watchlist"] = [dict(r, rank=i) for i, r in enumerate(eligible, 1)]
    if eligible:
        status = "COMPLETED"
    elif report["insufficient_data"]:
        status = "INSUFFICIENT_DATA"
    else:
        status = "NO_ELIGIBLE_CANDIDATES"
    return dict(report, status=status)
