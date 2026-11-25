"""Diluted equity scenarios for operating businesses, with conditional inverse solutions."""

from itertools import product

from . import upstream
from .contracts import CASES, DRIVERS, number, text


def drivers_for_horizon(case, years):
    defaults = {key: case[key] for key in (*DRIVERS, "basis")}
    return {**defaults, **case.get("by_horizon", {}).get(str(years), {})}


def assumptions(data):
    fields = {*DRIVERS, "basis"}
    limits = {
        "growth_pct": (-99, 500),
        "net_margin_pct": (-100, 100),
        "annual_dilution_pct": (-90, 500),
        "pe": (0.01, 1000),
    }
    for name in CASES:
        case = data[name]
        if not isinstance(case, dict) or not fields <= case.keys() <= fields | {"by_horizon"}:
            raise ValueError(f"{name}: expected four scenario drivers and an evidence rationale")
        overrides = case.get("by_horizon", {})
        if not isinstance(overrides, dict) or overrides.keys() - {"1", "3", "5"}:
            raise ValueError(f"{name}: unsupported scenario horizon")
        for years in (1, 3, 5):
            override = overrides.get(str(years), {})
            if (
                not isinstance(override, dict)
                or override.keys() - fields
                or (override and not text(override.get("basis")))
            ):
                raise ValueError(
                    f"{name}, year {years}: horizon changes require a documented basis"
                )
            drivers = drivers_for_horizon(case, years)
            if not text(drivers["basis"]):
                raise ValueError(f"{name}: missing evidence rationale")
            for key, allowed in limits.items():
                pair = drivers[key]
                if not isinstance(pair, list) or len(pair) != 2:
                    raise ValueError(f"{name}.{key}: expected [low, high]")
                low, high = [number(value, *allowed) for value in pair]
                if low > high:
                    raise ValueError(f"{name}.{key}: inverted range")
            if all(drivers[key][0] == drivers[key][1] for key in DRIVERS):
                raise ValueError(f"{name}: at least one scenario driver needs a range")
    return data


def bounds(values):
    # Retain precision for inverse calculations that use these endpoints as inputs.
    values = list(values)
    return [min(values), max(values)]


def project_case(revenue, shares, price, years, case):
    future_revenues = []
    future_shares = []
    profits = []
    prices = []
    for growth, margin, dilution, pe in product(*(case[key] for key in DRIVERS)):
        sales = revenue * (1 + growth / 100) ** years
        shares_at_exit = shares * (1 + dilution / 100) ** years
        income = sales * margin / 100
        future_revenues.append(sales)
        future_shares.append(shares_at_exit)
        profits.append(income)
        prices.append(upstream.scenario(income / shares_at_exit, pe, price, years))

    complete = all(result is not None for result in prices)
    band = {
        "assumptions": case,
        "revenue": bounds(future_revenues),
        "shares": bounds(future_shares),
        "net_income": bounds(profits),
        "status": "ESTIMATED" if complete else "INSUFFICIENT_DATA",
    }
    for key in ("implied_price", "upside_pct", "cagr_pct"):
        band[key] = bounds(result[key] for result in prices) if complete else None
    return band


def inverse_hurdle(target_price, revenue, years, base):
    assumptions = base["assumptions"]
    equity_values = [target_price * shares for shares in base["shares"]]
    profits = [equity / pe for equity, pe in product(equity_values, assumptions["pe"])]
    margins = assumptions["net_margin_pct"]
    sales = (
        [profit / (margin / 100) for profit, margin in product(profits, margins)]
        if min(margins) > 0
        else []
    )
    return {
        "target_price": target_price,
        "required_equity_value": bounds(equity_values),
        "required_net_income_at_assumed_pe": bounds(profits),
        "required_revenue_at_assumed_margin": bounds(sales) if sales else None,
        "required_revenue_cagr_pct": bounds(upstream.cagr(revenue, value, years) for value in sales)
        if sales
        else None,
        "required_net_margin_pct_at_projected_revenue": bounds(
            upstream.percent(profit, projected)
            for profit, projected in product(profits, base["revenue"])
        ),
        "required_pe_at_projected_income": bounds(
            equity / profit for equity, profit in product(equity_values, base["net_income"])
        )
        if min(base["net_income"]) > 0
        else None,
        "status": "ESTIMATED" if sales and min(base["net_income"]) > 0 else "INSUFFICIENT_DATA",
    }


def projections(financials, market, cases):
    revenue, shares, price = financials["revenue"], market["shares_outstanding"], market["price"]
    results = {}
    for years in (1, 3, 5):
        bands = {
            name: project_case(revenue, shares, price, years, drivers_for_horizon(case, years))
            for name, case in cases.items()
        }
        hurdles = {
            f"{multiple}x": inverse_hurdle(price * multiple, revenue, years, bands["base"])
            for multiple in (2, 5, 10)
        }
        results[str(years)] = {"scenarios": bands, "return_hurdles": hurdles}
    return results
