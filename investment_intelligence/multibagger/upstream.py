"""Use the existing skill implementations without installing or copying them."""

import importlib.util
import sys
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[2] / "skills"
GROWTH = SKILLS / "us-undervalued-growth-screener/scripts"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# The upstream financials module uses absolute sibling imports. The Codex entry
# runs in a dedicated interpreter. Restore the import search path after loading.
sys.path.insert(0, str(GROWTH))
try:
    from evaluation_common import RUNTIME_FINGERPRINT, _cagr, _pct, _scenario
    from evaluation_financials import _calculate_financial_metrics
finally:
    sys.path.pop(0)

flow = load("mb_flow_quality", SKILLS / "institutional-flow-tracker/scripts/data_quality.py")
quality = load("mb_document_quality", SKILLS / "data-quality-checker/scripts/check_data_quality.py")
technical = load("mb_weekly_prices", SKILLS / "technical-analyst/scripts/weekly_price_action.py")
cagr = _cagr
percent = _pct
scenario = _scenario
growth_version = RUNTIME_FINGERPRINT


def accounts(f, market_cap, source_ids):
    histories = {}
    for field, previous, current in (
        ("revenue", f["prior_revenue"], f["revenue"]),
        (
            "gaap_eps",
            f["prior_income"] / f["prior_diluted_shares"],
            f["income"] / f["diluted_shares"],
        ),
        ("diluted_shares", f["prior_diluted_shares"], f["diluted_shares"]),
    ):
        histories[field] = [{"value": previous}, {"value": current}]
    path = "financials.cash_flow_ttm.reported_ttm"
    candidate = {
        "identity": {"market_cap": market_cap},
        "financials": {
            "revenue_ttm": f["revenue"],
            "sbc_ttm": f["sbc"],
            "total_debt": f["debt"],
            "cash_classification": {"corporate_cash": f["unrestricted_cash"]},
            "cash_flow_ttm": {
                "method": "reported_ttm",
                "operating_cash_flow": f["ocf"],
                "capex_cash_outflow": f["capex"],
                "source_ids": source_ids,
            },
            "histories": histories,
        },
    }
    metrics, warnings, review, unresolved = _calculate_financial_metrics(
        candidate, {}, {sid: {"supports": [path]} for sid in source_ids}
    )
    if warnings or review or unresolved:
        raise ValueError(f"upstream accounts reconciliation: {warnings + review + unresolved}")
    return metrics
