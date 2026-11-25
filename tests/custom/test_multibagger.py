"""Regression, accounting and point-in-time checks for the custom discovery skill."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from investment_intelligence.multibagger.contracts import ARCHIVE_METADATA, FLAGS, config, read_json
from investment_intelligence.multibagger.engine import screen
from investment_intelligence.multibagger.valuation import projections

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "examples/custom/multibagger/synthetic.json"
GROUPS = ("ranked_watchlist", "speculative", "insufficient_data", "excluded")


@pytest.fixture
def snapshot():
    return read_json(FIXTURE)


def evaluate(snapshot, overrides=None, archive=None):
    return screen(snapshot, config(overrides or {}), archive)


def first_company(report):
    return next(row for group in GROUPS for row in report[group] if row["id"] == "XNAS:XFIX")


def sections(snapshot):
    return snapshot["companies"][0]["sections"]


def invoke(*args, **kwargs):
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "investment_intelligence",
            "skill",
            "multibagger-discovery-screener",
            *map(str, args),
        ],
        cwd=ROOT,
        capture_output=True,
        **kwargs,
    )


def test_codex_offline_demo_is_repeatable_and_traceable(snapshot):
    marker = "fixture-test-private-marker"
    env = {**os.environ, "FMP_API_KEY": marker}
    one = invoke("--input", FIXTURE, env=env, check=True)
    two = invoke("--input", FIXTURE, env=env, check=True)
    assert one.stdout == two.stdout and not one.stderr
    assert marker.encode() not in one.stdout
    report = json.loads(one.stdout)
    expected_digest = hashlib.sha256(
        json.dumps(snapshot, separators=(",", ":"), sort_keys=True).encode()
    ).hexdigest()
    assert report["snapshot_sha256"] == expected_digest
    for name, digest in report["calculation_files_sha256"].items():
        assert (
            hashlib.sha256((ROOT / name).read_text(encoding="utf-8").encode("utf-8")).hexdigest()
            == digest
        )
    assert "investment_intelligence/multibagger/valuation.py" in report["calculation_files_sha256"]
    assert report["status"] == "COMPLETED" and report["dataset"] == "synthetic"
    assert [[r["id"] for r in report[g]] for g in GROUPS] == [
        ["XNAS:XFIX"],
        ["XNYS:YFIX"],
        ["XNAS:ZFIX"],
        [],
    ]
    healthy, distressed = report["ranked_watchlist"][0], report["speculative"][0]
    assert healthy["rank"] == 1 and "rank" not in distressed
    assert healthy["attractiveness_score"] == distressed["attractiveness_score"] == 84.51
    assert (
        healthy["financial_risk"]["score"] == 0 and distressed["financial_risk"]["score"] == 57.14
    )
    assert report["insufficient_data"][0]["evidence_confidence"] < healthy["evidence_confidence"]
    assert report["insufficient_data"][0]["financial_risk"]["score"] is None
    assert healthy["valuation_horizons"]["5"]["scenarios"]["base"]["implied_price"] == [
        18.0441,
        42.0589,
    ]
    assert all(
        report["sources"][s]["published_at"]
        for refs in healthy["source_refs"].values()
        for s in refs
    )
    assert healthy["financial_performance"]["derived"]["standard_fcf"] == 72_000_000
    assert healthy["current_valuation"]["enterprise_value"] == 820_000_000


@pytest.mark.parametrize("field", FLAGS)
def test_each_severe_filing_risk_is_speculative_even_with_strong_factors(snapshot, field):
    sections(snapshot)["risk_review"]["data"][field]["severity"] = "severe"
    row = first_company(evaluate(snapshot))
    assert row["status"] == "SPECULATIVE" and row["attractiveness_score"] == 84.51
    assert row["financial_risk"]["checks"][field]["severity"] == "severe"


@pytest.mark.parametrize(
    ("section", "changes", "check"),
    [
        ("accounts", {"ocf": -200_000_000}, "cash_runway"),
        ("accounts", {"unrestricted_cash": 5_000_000}, "debt_maturity"),
        ("accounts", {"prior_diluted_shares": 75_000_000}, "historical_dilution"),
        ("exposures", {"potential_dilution_pct": 20}, "potential_dilution"),
        ("accounts", {"sbc": 50_000_000}, "share_based_compensation"),
        ("exposures", {"largest_customer_revenue_pct": 30}, "customer_concentration"),
        ("market", {"avg_daily_value_60d": 500_000}, "liquidity"),
    ],
)
def test_numeric_risk_gates(snapshot, section, changes, check):
    sections(snapshot)[section]["data"].update(changes)
    row = first_company(evaluate(snapshot))
    assert row["financial_risk"]["checks"][check]["severity"] == "severe"
    assert row["status"] == "SPECULATIVE"


@pytest.mark.parametrize(
    "stage", ["announcement", "mou", "pilot", "binding_contract", "commercial_deployment"]
)
def test_distinguishes_commercial_stages(snapshot, stage):
    sections(snapshot)["commercial"]["data"].update(stage=stage, recognized_revenue=0)
    row = first_company(evaluate(snapshot))
    if stage in {"announcement", "mou", "pilot"}:
        assert (
            "commercial traction unverified" in row["blockers"]
            and row["status"] == "INSUFFICIENT_DATA"
        )
    else:
        assert (
            row["status"] == "ELIGIBLE" and row["commercial_validation"]["recognized_revenue"] == 0
        )


def test_revenue_needs_specific_filing_and_comparability(snapshot):
    snapshot["sources"]["XFIX-commercial"]["kind"] = "issuer"
    assert "filing support" in first_company(evaluate(snapshot))["issues"]["commercial"]
    snapshot["sources"]["XFIX-commercial"]["kind"] = "filing"
    sections(snapshot)["commercial"]["data"]["stage"] = "pilot"
    assert "stage disagrees" in first_company(evaluate(snapshot))["issues"]["commercial"]


@pytest.mark.parametrize(
    ("section", "key", "value"),
    [
        ("accounts", "basis", "management_forecast"),
        ("accounts", "prior_fiscal_end", "2022-12-31"),
        ("market", "currency", "SGD"),
        ("commercial", "currency", "SGD"),
        ("commercial", "fiscal_end", "2023-12-31"),
        ("exposures", "units", "millions"),
        ("industry", "obtainable_market", 13_000_000_000),
        ("thesis", "invalidation", "UNKNOWN"),
        ("moat", "rationale", None),
    ],
)
def test_required_data_cannot_be_substituted(snapshot, section, key, value):
    sections(snapshot)[section]["data"][key] = value
    row = first_company(evaluate(snapshot))
    assert row["status"] == "INSUFFICIENT_DATA" and section in row["issues"]


@pytest.mark.parametrize(
    ("sid", "field", "value"),
    [
        ("XFIX-market", "observed_at", "2025-03-01T15:00:00Z"),
        ("XFIX-accounts", "published_at", "2025-04-01T00:00:00Z"),
        ("XFIX-accounts", "observed_at", "2024-11-30T00:00:00Z"),
        ("XFIX-accounts", "kind", "news"),
        ("XFIX-accounts", "listing", "XNYS:YFIX"),
        ("XFIX-accounts", "supports", ["accounts.revenue"]),
        ("XFIX-accounts", "uri", "https://filings.example.invalid/a?api_key=private-marker"),
    ],
)
def test_rejects_stale_future_secondary_unscoped_and_credentialed_citations(
    snapshot, sid, field, value
):
    snapshot["sources"][sid][field] = value
    report = evaluate(snapshot)
    assert first_company(report)["status"] == "INSUFFICIENT_DATA" and sid not in report["sources"]
    assert "private-marker" not in json.dumps(report)


def test_no_hindsight_and_no_survivor_only_ranking(snapshot):
    snapshot["mode"] = "historical"
    incomplete = evaluate(snapshot)
    assert (
        not incomplete["ranked_watchlist"] and "availability" in incomplete["universe_blockers"][0]
    )
    snapshot["companies"][2]["sections"]["accounts"]["review"] = "verified"
    complete = evaluate(snapshot)
    assert complete["status"] == "COMPLETED"
    sections(snapshot)["assumptions"]["prepared_at"] = "2026-01-01T09:00:00Z"
    assert evaluate(snapshot)["status"] == "INSUFFICIENT_DATA"
    snapshot["sources"]["roster"]["includes_later_delisted"] = False
    assert "delisted" in evaluate(snapshot)["universe_blockers"][0]
    snapshot["sources"]["roster"]["includes_later_delisted"] = True
    snapshot["companies"].pop()
    result = evaluate(snapshot)
    assert result["missing_members"] == ["XNAS:ZFIX"] and not result["ranked_watchlist"]


def test_real_archives_require_digest_excerpt_and_roster_vintage(snapshot, tmp_path):
    snapshot["dataset"] = "research"
    for sid, source in snapshot["sources"].items():
        source["uri"] = "https://archive.example.invalid/" + sid
        source["document"] = sid + ".txt"
        if sid == "roster":
            archived = {
                k: source[k]
                for k in ("members", "observed_at", "point_in_time", "includes_later_delisted")
            }
        else:
            listing_row = next(r for r in snapshot["companies"] if r["id"] == source["listing"])
            section = source["supports"][0].split(".")[0]
            reviewed = listing_row["sections"][section]["data"]
            archived = {"claims": {f"{section}.{k}": v for k, v in reviewed.items()}}
        archived["text"] = f"Primary extract for {sid}: {json.dumps(archived, sort_keys=True)}"
        archived["source"] = {k: source[k] for k in ARCHIVE_METADATA}
        raw = json.dumps(archived, sort_keys=True)
        source["excerpt"] = archived["text"]
        source["sha256"] = hashlib.sha256(raw.encode()).hexdigest()
        (tmp_path / source["document"]).write_bytes(raw.encode())
    assert not evaluate(snapshot)["ranked_watchlist"]
    report = evaluate(snapshot, archive=tmp_path)
    assert report["status"] == "COMPLETED"
    assert "excerpt" not in report["sources"]["XFIX-accounts"]
    inputs = tmp_path / "snapshots"
    inputs.mkdir()
    input_file = inputs / "reviewed.json"
    input_file.write_text(json.dumps(snapshot), encoding="utf-8")
    cli = json.loads(invoke("--input", input_file, "--evidence-dir", tmp_path, check=True).stdout)
    assert cli["ranked_watchlist"] == report["ranked_watchlist"]
    assert not json.loads(invoke("--input", input_file, check=True).stdout)["ranked_watchlist"]
    source = snapshot["sources"]["XFIX-accounts"]
    publication = source["published_at"]
    source["published_at"] = "2025-01-01T01:00:00Z"
    assert first_company(evaluate(snapshot, archive=tmp_path))["status"] == "INSUFFICIENT_DATA"
    source["published_at"] = publication
    sections(snapshot)["accounts"]["data"]["revenue"] += 1
    changed = first_company(evaluate(snapshot, archive=tmp_path))
    assert changed["status"] == "INSUFFICIENT_DATA" and "revenue" in changed["issues"]["accounts"]
    sections(snapshot)["accounts"]["data"]["revenue"] -= 1
    (tmp_path / "XFIX-accounts.txt").write_text("altered filing")
    assert first_company(evaluate(snapshot, archive=tmp_path))["status"] == "INSUFFICIENT_DATA"
    snapshot["sources"]["XFIX-accounts"]["document"] = "../outside"
    assert first_company(evaluate(snapshot, archive=tmp_path))["status"] == "INSUFFICIENT_DATA"
    snapshot["sources"]["roster"]["includes_later_delisted"] = False
    assert evaluate(snapshot, archive=tmp_path)["status"] == "INSUFFICIENT_DATA"


def test_coverage_and_configurable_weights(snapshot):
    settings = config({})
    assert list(settings["weights"].values()) == [15, 15, 15, 15, 15, 10, 5, 5, 5]
    sections(snapshot)["institutional"]["data"]["prior_holders"] = 0
    sections(snapshot)["technical"]["data"]["bars"][-1]["date"] = "2026-01-01"
    row = first_company(evaluate(snapshot))
    assert row["evidence_coverage_pct"] == 90 and row["evidence_confidence"] < 100
    assert row["attractiveness_range"][1] - row["attractiveness_range"][0] == pytest.approx(10)
    weights = {"momentum": 0, "institutional": 0, "moat": 25}
    reweighted = first_company(evaluate(snapshot, {"weights": weights}))
    assert reweighted["evidence_coverage_pct"] == 100
    assert reweighted["attractiveness_score"] != row["attractiveness_score"]


@pytest.mark.parametrize(
    "universe",
    [
        {"countries": ["SG"]},
        {"exchanges": ["XSES"]},
        {"sectors": ["Energy"]},
        {"max_cap": 800_000_000},
        {"min_daily_value": 3_000_000},
    ],
)
def test_universe_filters(snapshot, universe):
    assert first_company(evaluate(snapshot, {"universe": universe}))["status"] == "EXCLUDED"


def test_larger_operating_company_can_qualify_and_horizon_affects_returns(snapshot):
    # 20-for-1 scale of the entire business preserves per-share economics.
    s = sections(snapshot)
    s["market"]["data"]["shares_outstanding"] *= 20
    for key in (
        "revenue",
        "prior_revenue",
        "income",
        "prior_income",
        "diluted_shares",
        "prior_diluted_shares",
        "ocf",
        "capex",
        "sbc",
        "debt",
        "unrestricted_cash",
    ):
        s["accounts"]["data"][key] *= 20
    for section, key in [
        ("exposures", "debt_due_12m"),
        ("commercial", "recognized_revenue"),
        ("industry", "tam"),
        ("industry", "obtainable_market"),
    ]:
        s[section]["data"][key] *= 20
    assert first_company(evaluate(snapshot))["status"] == "EXCLUDED"
    allowed = first_company(evaluate(snapshot, {"universe": {"max_cap": 20_000_000_000}}))
    assert allowed["status"] == "ELIGIBLE"
    shorter = first_company(
        evaluate(snapshot, {"universe": {"max_cap": 20_000_000_000, "horizon_years": 1}})
    )
    assert shorter["factors"]["valuation"] != allowed["factors"]["valuation"]


def test_forward_and_inverse_math_with_dilution():
    band = {
        "growth_pct": [10, 10],
        "net_margin_pct": [20, 20],
        "annual_dilution_pct": [10, 10],
        "pe": [10, 10],
        "basis": "fixture",
    }
    out = projections(
        {"revenue": 100},
        {"shares_outstanding": 10, "price": 10},
        {case: band for case in ("bear", "base", "bull")},
    )
    for years in (1, 3, 5):
        result = out[str(years)]
        base = result["scenarios"]["base"]
        assert base["shares"][0] == pytest.approx(10 * 1.1**years)
        assert base["implied_price"] == [20, 20] and base["upside_pct"] == [100, 100]
        for target in (2, 5, 10):
            required = result["return_hurdles"][f"{target}x"]
            assert required["required_equity_value"][0] == pytest.approx(100 * target * 1.1**years)
            assert required["required_net_income_at_assumed_pe"][0] == pytest.approx(
                10 * target * 1.1**years
            )
            assert required["required_revenue_at_assumed_margin"][0] == pytest.approx(
                50 * target * 1.1**years
            )
            assert required["required_net_margin_pct_at_projected_revenue"][0] == pytest.approx(
                10 * target
            )
            assert required["required_pe_at_projected_income"][0] == pytest.approx(5 * target)
    assert out["1"]["return_hurdles"]["2x"]["required_revenue_cagr_pct"] == pytest.approx([10, 10])


def test_loss_endpoint_and_unobtainable_market_block_ranking(snapshot):
    s = sections(snapshot)
    s["assumptions"]["data"]["base"]["net_margin_pct"][0] = -1
    row = first_company(evaluate(snapshot))
    assert row["status"] == "INSUFFICIENT_DATA"
    values = row["valuation_horizons"]["5"]
    assert values["scenarios"]["base"]["implied_price"] is None
    assert values["return_hurdles"]["10x"]["required_revenue_at_assumed_margin"] is None
    s["assumptions"]["data"]["base"]["net_margin_pct"][0] = 13
    s["industry"]["data"]["obtainable_market"] = 700_000_000
    assert "obtainable market" in first_company(evaluate(snapshot))["blockers"][-1]


@pytest.mark.parametrize(
    "overrides",
    [
        {"weights": {"industry": 14}},
        {"universe": {"horizon_years": 4}},
        {"thresholds": {"speculative_risk_score": 110}},
        {"universe": {"max_cap": 100}},
        {"thresholds": {"runway_months": 0}},
        {"unknown": {}},
    ],
)
def test_invalid_config(overrides):
    with pytest.raises(ValueError):
        config(overrides)


def test_cli_rejects_duplicate_input_and_reads_config(tmp_path):
    invalid = tmp_path / "bad.json"
    invalid.write_text('{"companies":[],"companies":[]}')
    failed = invoke("--input", invalid)
    assert failed.returncode == 2 and not failed.stdout and b"duplicate JSON" in failed.stderr
    overrides = tmp_path / "policy.json"
    overrides.write_text('{"universe":{"countries":["SG"]}}')
    report = json.loads(invoke("--input", FIXTURE, "--config", overrides, check=True).stdout)
    assert report["status"] == "NO_ELIGIBLE_CANDIDATES" and len(report["excluded"]) == 3


def test_quote_denomination_does_not_create_attractiveness(snapshot):
    before = first_company(evaluate(snapshot))
    s = sections(snapshot)
    # All historical accounting and price observations use the same 10-for-1 split basis.
    s["market"]["data"]["price"] /= 10
    s["market"]["data"]["shares_outstanding"] *= 10
    for field in ("diluted_shares", "prior_diluted_shares"):
        s["accounts"]["data"][field] *= 10
    for bar in s["technical"]["data"]["bars"]:
        for field in ("open", "high", "low", "close"):
            bar[field] /= 10
    after = first_company(evaluate(snapshot))
    for field in ("status", "attractiveness_score", "financial_risk", "evidence_confidence"):
        assert after[field] == before[field]
    assert (
        after["valuation_horizons"]["5"]["scenarios"]["bull"]["upside_pct"]
        == before["valuation_horizons"]["5"]["scenarios"]["bull"]["upside_pct"]
    )


def test_eligible_ties_and_absent_ineligible_member(snapshot):
    snapshot["companies"][2]["sections"]["accounts"]["review"] = "verified"
    expected = ["XNAS:XFIX", "XNAS:ZFIX"]
    for _ in range(2):
        ranked = evaluate(snapshot)["ranked_watchlist"]
        assert [r["id"] for r in ranked] == expected
        assert [r["rank"] for r in ranked] == [1, 2]
        snapshot["companies"].reverse()
    # A known speculative member cannot quietly disappear from a snapshot ranking.
    snapshot["companies"] = [r for r in snapshot["companies"] if r["id"] != "XNYS:YFIX"]
    result = evaluate(snapshot)
    assert result["status"] == "INSUFFICIENT_DATA"
    assert result["missing_members"] == ["XNYS:YFIX"] and not result["ranked_watchlist"]


def test_missing_risk_and_speculative_threshold(snapshot):
    sections(snapshot)["risk_review"]["data"]["refinancing"]["severity"] = "elevated"
    assert first_company(evaluate(snapshot))["financial_risk"]["classification"] == "ELEVATED"
    row = first_company(evaluate(snapshot, {"thresholds": {"speculative_risk_score": 20}}))
    assert row["status"] == "SPECULATIVE"
    del sections(snapshot)["risk_review"]["data"]["accounting_irregularities"]
    row = first_company(evaluate(snapshot))
    assert row["status"] == "INSUFFICIENT_DATA"
    assert row["financial_risk"]["classification"] == "UNKNOWN"
    assert row["financial_risk"]["checks"]["accounting_irregularities"]["severity"] == "UNKNOWN"


def test_unverified_risk_date_and_momentum_cannot_override_missing_accounts(snapshot):
    snapshot["sources"]["XFIX-risk_review"]["observed_at"] = "2024-07-01T10:00:00Z"
    row = first_company(evaluate(snapshot))
    assert row["financial_risk"]["checks"]["refinancing"]["severity"] == "UNKNOWN"
    del sections(snapshot)["accounts"]
    row = first_company(
        evaluate(
            snapshot,
            {"weights": {key: (100 if key == "momentum" else 0) for key in config({})["weights"]}},
        )
    )
    assert row["status"] == "INSUFFICIENT_DATA" and row["factors"]["adoption"] is None


def test_equity_method_excludes_funds(snapshot):
    sections(snapshot)["profile"]["data"]["instrument_type"] = "etf"
    row = first_company(evaluate(snapshot))
    assert row["status"] == "EXCLUDED" and "instrument type" in row["exclusions"][0]


def test_horizon_specific_inputs_control_forward_and_reverse_requirements(snapshot):
    cases = sections(snapshot)["assumptions"]["data"]
    row = first_company(evaluate(snapshot))
    original = row["valuation_horizons"]
    cases["base"]["by_horizon"]["1"] = {
        "net_margin_pct": [-2, 3],
        "basis": "First-year tooling expense",
    }
    changed = first_company(evaluate(snapshot))
    assert changed["valuation_horizons"]["1"]["scenarios"]["base"]["status"] == "INSUFFICIENT_DATA"
    assert (
        changed["valuation_horizons"]["1"]["return_hurdles"]["2x"][
            "required_revenue_at_assumed_margin"
        ]
        is None
    )
    assert changed["valuation_horizons"]["5"] == original["5"] and changed["status"] == "ELIGIBLE"
    cases["base"]["by_horizon"]["1"].pop("basis")
    assert "documented basis" in first_company(evaluate(snapshot))["issues"]["assumptions"]
