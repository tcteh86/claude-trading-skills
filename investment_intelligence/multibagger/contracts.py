"""Validated configuration and claim-specific evidence records."""

import hashlib
import json
import math
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

DEFAULTS = Path(__file__).with_name("defaults.json")
PROFILE = (
    "company_name",
    "ticker",
    "instrument_type",
    "headquarters",
    "exchange",
    "country",
    "sector",
    "products_services",
    "customers",
    "competitors",
    "investment_theme",
)
THESIS = ("bull_case", "bear_case", "catalysts", "invalidation", "monitoring_metrics")
ACCOUNTS = (
    "basis",
    "currency",
    "units",
    "fiscal_end",
    "prior_fiscal_end",
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
)
FLAGS = (
    "bankruptcy_going_concern",
    "refinancing",
    "regulatory_exposure",
    "delisting",
    "reverse_splits",
    "related_party_transactions",
    "accounting_irregularities",
)
STAGES = {
    "announcement": 5,
    "mou": 10,
    "pilot": 25,
    "binding_contract": 50,
    "commercial_deployment": 70,
    "recognized_revenue": 100,
}
CASES = ("bear", "base", "bull")
DRIVERS = ("growth_pct", "net_margin_pct", "annual_dilution_pct", "pe")
PRIMARY = {"filing", "issuer", "exchange", "regulator", "customer", "industry_statistics"}


def parse_json(raw):
    def unique(pairs):
        result = {}
        for k, v in pairs:
            if k in result:
                raise ValueError(f"duplicate JSON key: {k}")
            result[k] = v
        return result

    data = json.loads(raw, object_pairs_hook=unique)
    json.dumps(data, allow_nan=False)
    return data


def read_json(path):
    return parse_json(path.read_text(encoding="utf-8"))


def number(value, minimum=None, maximum=None):
    if type(value) not in (float, int) or not math.isfinite(value):
        raise ValueError("expected a finite number")
    if minimum is not None and value < minimum or maximum is not None and value > maximum:
        raise ValueError("number outside allowed range")
    return value


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("expected an ISO timestamp")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.utcoffset() is None:
        raise ValueError("timestamp needs a timezone")
    return dt


def config(overrides):
    settings = read_json(DEFAULTS)
    if not isinstance(overrides, dict) or set(overrides) - settings.keys():
        raise ValueError("unknown config section")
    for section, values in overrides.items():
        if not isinstance(values, dict) or set(values) - settings[section].keys():
            raise ValueError(f"unknown config key in {section}")
        settings[section].update(values)
    weights = settings["weights"]
    if not math.isclose(sum(number(v, 0, 100) for v in weights.values()), 100, abs_tol=1e-8):
        raise ValueError("weights must total 100")
    u = settings["universe"]
    for k in ("countries", "exchanges", "sectors"):
        if not isinstance(u[k], list) or not all(text(v) for v in u[k]):
            raise ValueError(f"invalid {k} filter")
    if (
        not isinstance(u["currency"], str)
        or len(u["currency"]) != 3
        or not u["currency"].isalpha()
        or not u["currency"].isupper()
    ):
        raise ValueError("currency must be an uppercase currency code")
    number(u["min_cap"], 0)
    number(u["max_cap"], u["min_cap"])
    number(u["min_daily_value"], 0)
    if type(u["horizon_years"]) is not int or u["horizon_years"] not in (1, 3, 5):
        raise ValueError("ranking horizon must be 1, 3 or 5 years")
    for k, v in settings["thresholds"].items():
        if k in ("min_confidence", "min_attractiveness", "speculative_risk_score"):
            number(v, 0, 100)
        elif number(v) <= 0:
            raise ValueError(f"{k} must be positive")
    return settings


def text(value):
    return (
        isinstance(value, str)
        and value.strip()
        and value.strip().upper() not in {"UNKNOWN", "N/A", "INSUFFICIENT_DATA"}
    )


ARCHIVE_METADATA = ("listing", "kind", "uri", "revision", "locator", "observed_at", "published_at")


class Evidence:
    def __init__(self, snapshot, settings, evidence_dir=None):
        self.cutoff = timestamp(snapshot["as_of"])
        self.thresholds = settings["thresholds"]
        self.synthetic = snapshot["dataset"] == "synthetic"
        self.root = Path(evidence_dir).resolve() if evidence_dir else None
        self.documents = {}
        self.sources = snapshot["sources"]
        if not isinstance(self.sources, dict):
            raise ValueError("sources must be keyed by ID")

    def archived_claims(self, sid, source):
        """Load the reviewed extraction once and bind its normalized claims to the source digest."""
        if sid in self.documents:
            return self.documents[sid]
        claims = {}
        try:
            relative = Path(source["document"])
            if not self.root or relative.is_absolute() or ".." in relative.parts:
                return {}
            path = (self.root / relative).resolve()
            if not path.is_relative_to(self.root) or not path.is_file():
                return {}
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() != source["sha256"]:
                return {}
            archive = parse_json(data.decode("utf-8"))
            if any(archive["source"][k] != source[k] for k in ARCHIVE_METADATA):
                return {}
            excerpt = source["excerpt"]
            if (
                not text(excerpt)
                or not isinstance(archive["text"], str)
                or excerpt not in archive["text"]
            ):
                return {}
            if source["listing"] == "UNIVERSE":
                vintage = ("observed_at", "point_in_time", "includes_later_delisted")
                if any(archive.get(k) != source.get(k) for k in vintage):
                    return {}
                claims = {"universe.members": archive["members"]}
            elif isinstance(archive["claims"], dict):
                claims = archive["claims"]
        except (KeyError, UnicodeError, OSError, ValueError, TypeError):
            claims = {}
        self.documents[sid] = claims
        return claims

    def verified(self, sid, listing, claim, kinds, max_age, value, prepared=None):
        source = self.sources.get(sid, {})
        if (
            not isinstance(source, dict)
            or source.get("listing") != listing
            or source.get("kind") not in kinds
        ):
            return False
        if not all(text(source.get(k)) for k in ("uri", "locator", "verified_by", "revision")):
            return False
        uri = urlsplit(source["uri"])
        valid_uri = uri.scheme == "https" or (self.synthetic and uri.scheme == "fixture")
        if not valid_uri or not uri.hostname or uri.username or uri.password:
            return False
        if any(
            any(
                word in key.lower()
                for word in ("key", "token", "signature", "credential", "password")
            )
            for key, _ in parse_qsl(uri.query)
        ):
            return False
        if not isinstance(source.get("supports"), list) or claim not in source["supports"]:
            return False
        try:
            observed = timestamp(source["observed_at"])
            published = timestamp(source["published_at"])
            retrieved = timestamp(source["retrieved_at"])
        except (KeyError, ValueError):
            return False
        if not (
            observed <= published <= (prepared or self.cutoff)
            and published <= retrieved
            and (self.cutoff - observed).total_seconds() <= max_age * 86400
        ):
            return False
        if not self.synthetic:
            claims = self.archived_claims(sid, source)
            if claim not in claims:
                return False
            if claims[claim] != value:
                if listing == "UNIVERSE":
                    return False
                raise ValueError(f"{claim}: input conflicts with a reviewed primary extract")
        return True

    def citation(self, sid):
        fields = (
            "kind",
            "listing",
            "uri",
            "revision",
            "locator",
            "observed_at",
            "published_at",
            "retrieved_at",
            "supports",
            "sha256",
            "verified_by",
            "members",
            "point_in_time",
            "includes_later_delisted",
        )
        return {k: self.sources[sid][k] for k in fields if k in self.sources[sid]}

    def section(self, row, name, fields, kinds=PRIMARY):
        section = row.get("sections", {}).get(name, {})
        data = section.get("data", {})
        refs = section.get("sources", [])
        age_key = {
            "market": "max_market_age_days",
            "exposures": "max_risk_age_days",
            "risk_review": "max_risk_age_days",
        }.get(name, "max_report_age_days")
        age = self.thresholds[age_key]
        prepared = timestamp(section["prepared_at"])
        if prepared > self.cutoff:
            raise ValueError("assessment was prepared after cutoff")
        if (
            section.get("review") != "verified"
            or not isinstance(refs, list)
            or not all(isinstance(s, str) for s in refs)
        ):
            raise ValueError("missing or unresolved primary-source review")
        cited = {}
        for key in fields:
            supporting = {
                sid
                for sid in refs
                if self.verified(
                    sid, row["id"], f"{name}.{key}", kinds, age, data.get(key), prepared
                )
            }
            if key not in data or data[key] is None or not supporting:
                raise ValueError(f"{key}: missing verified point-in-time evidence")
            cited[f"{name}.{key}"] = sorted(supporting)
        return {k: data[k] for k in fields}, cited
