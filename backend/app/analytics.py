"""Synthetic analytics for the dashboards.

Deterministic (seeded) so the dashboards look alive and consistent without a real
warehouse. Everything here would be a query over the documents table in production.
"""
from __future__ import annotations

import random
from datetime import date, timedelta

_DOC_TYPES = [
    "commercial_invoice", "certificate_of_origin", "house_air_waybill",
    "customs_declaration", "purchase_order", "goods_receipt_note",
    "vendor_invoice", "gst_certificate", "bank_statement",
]
_WORKFLOWS = ["customs", "po2pay", "contracts", "finance"]
_OFFICERS = [
    ("Omar Al-Ghamdi", "customs_officer"),
    ("Sara Al-Harbi", "manager"),
    ("Yousef Al-Dosari", "customs_officer"),
    ("Noura Al-Qahtani", "customs_officer"),
    ("Faisal Al-Shehri", "manager"),
]
_RULES = [
    "hs_code_duty_consistency", "three_way_match", "running_balance",
    "gstin_checksum", "line_totals_sum", "coo_invoice_cross_check",
    "hawb_weight_consistency", "amount_in_words_matches",
]


def _rng(seed: int) -> random.Random:
    return random.Random(seed)


def timeseries(days: int = 30) -> list[dict]:
    r = _rng(42)
    today = date.today()
    out = []
    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        weekday = d.weekday()
        base = 120 if weekday < 5 else 45
        total = base + r.randint(-20, 40)
        auto = int(total * r.uniform(0.66, 0.82))
        review = total - auto
        out.append({"date": d.isoformat(), "total": total, "auto": auto, "review": review})
    return out


def summary() -> dict:
    ts = timeseries(30)
    total = sum(d["total"] for d in ts)
    auto = sum(d["auto"] for d in ts)
    review = sum(d["review"] for d in ts)
    return {
        "documents_30d": total,
        "auto_approved": auto,
        "in_review": review,
        "straight_through_rate": round(auto / total, 3) if total else 0,
        "avg_confidence": 0.91,
        "avg_processing_seconds": 3.4,
        "hours_saved_30d": round(total * 4.5 / 60, 1),
        "accuracy": 0.983,
        "trend_pct": 12.4,
    }


def by_type() -> list[dict]:
    r = _rng(7)
    return sorted(
        ({"type": t, "count": r.randint(120, 900)} for t in _DOC_TYPES),
        key=lambda x: -x["count"],
    )


def by_workflow() -> list[dict]:
    r = _rng(11)
    return [{"workflow": w, "count": r.randint(400, 1600)} for w in _WORKFLOWS]


def routing() -> dict:
    s = summary()
    return {"auto_approved": s["auto_approved"], "in_review": s["in_review"]}


def confidence_buckets() -> list[dict]:
    r = _rng(19)
    labels = ["<70%", "70–80%", "80–90%", "90–95%", "95–100%"]
    weights = [4, 8, 18, 34, 36]
    return [{"bucket": l, "count": w * 10 + r.randint(0, 30)} for l, w in zip(labels, weights)]


def top_failed_rules() -> list[dict]:
    r = _rng(23)
    return sorted(
        ({"rule": rule, "failures": r.randint(8, 120)} for rule in _RULES),
        key=lambda x: -x["failures"],
    )[:6]


def by_officer() -> list[dict]:
    r = _rng(29)
    return sorted(
        (
            {
                "name": name,
                "role": role,
                "processed": r.randint(180, 640),
                "corrections": r.randint(10, 90),
                "avg_confidence": round(r.uniform(0.86, 0.96), 3),
            }
            for name, role in _OFFICERS
        ),
        key=lambda x: -x["processed"],
    )


def dashboard() -> dict:
    return {
        "summary": summary(),
        "timeseries": timeseries(30),
        "by_type": by_type(),
        "by_workflow": by_workflow(),
        "routing": routing(),
        "confidence_buckets": confidence_buckets(),
        "top_failed_rules": top_failed_rules(),
        "by_officer": by_officer(),
    }


def insights() -> list[dict]:
    """The 'Analyze' output — generated narrative insights over the data."""
    s = summary()
    tr = top_failed_rules()
    officers = by_officer()
    return [
        {
            "title": "Straight-through processing is healthy",
            "detail": f"{s['straight_through_rate'] * 100:.0f}% of documents auto-approved in the last 30 days, "
            f"saving an estimated {s['hours_saved_30d']} hours of manual review.",
            "tone": "positive",
        },
        {
            "title": f"Top rule failure: {tr[0]['rule']}",
            "detail": f"{tr[0]['failures']} documents failed '{tr[0]['rule']}'. Consider a targeted "
            "vendor/HS-code data-quality campaign to reduce review load.",
            "tone": "warning",
        },
        {
            "title": "Reviewer load is uneven",
            "detail": f"{officers[0]['name']} processed {officers[0]['processed']} documents — "
            f"{officers[0]['processed'] - officers[-1]['processed']} more than the lightest reviewer. "
            "Rebalancing could cut turnaround time.",
            "tone": "info",
        },
        {
            "title": "Confidence is trending up",
            "detail": f"Average field confidence is {s['avg_confidence'] * 100:.0f}% with {s['accuracy'] * 100:.1f}% "
            "post-review accuracy — extraction quality is stable.",
            "tone": "positive",
        },
    ]


# --------------------------------------------------------------------------- #
# Customs geographic / trade analytics
# --------------------------------------------------------------------------- #
_COUNTRIES = [
    ("China", "CN"), ("India", "IN"), ("United Arab Emirates", "AE"), ("Germany", "DE"),
    ("United States", "US"), ("Turkey", "TR"), ("Egypt", "EG"), ("South Korea", "KR"),
    ("Italy", "IT"), ("Japan", "JP"), ("Poland", "PL"), ("Brazil", "BR"),
]
_DEST = "Saudi Arabia"


def by_origin_country() -> list[dict]:
    r = _rng(101)
    data = [{"country": c, "code": code, "count": r.randint(120, 1400)} for c, code in _COUNTRIES]
    return sorted(data, key=lambda x: -x["count"])


def trade_lanes() -> list[dict]:
    r = _rng(103)
    origins = by_origin_country()[:8]
    return sorted(
        (
            {"origin": o["country"], "origin_code": o["code"], "destination": _DEST, "count": int(o["count"] * r.uniform(0.5, 0.95))}
            for o in origins
        ),
        key=lambda x: -x["count"],
    )


def confidence_by_country() -> list[dict]:
    r = _rng(107)
    out = [
        {"country": c, "code": code, "avg_confidence": round(r.uniform(0.72, 0.97), 3), "docs": r.randint(80, 1200)}
        for c, code in _COUNTRIES
    ]
    return sorted(out, key=lambda x: x["avg_confidence"])


def destinations() -> list[dict]:
    """Where cleared consignments travel onward (re-export lanes)."""
    r = _rng(109)
    dests = ["Saudi Arabia", "Bahrain", "Kuwait", "Qatar", "Oman", "Jordan", "Iraq"]
    return sorted(
        ({"country": d, "count": r.randint(90, 900)} for d in dests),
        key=lambda x: -x["count"],
    )


def geo() -> dict:
    conf = confidence_by_country()
    return {
        "by_origin": by_origin_country(),
        "trade_lanes": trade_lanes(),
        "confidence_by_country": conf,
        "destinations": destinations(),
        "lowest_confidence": conf[:3],
        "highest_confidence": list(reversed(conf))[:3],
    }


def geo_insights() -> list[dict]:
    lanes = trade_lanes()
    conf = confidence_by_country()
    return [
        {
            "title": f"Busiest lane: {lanes[0]['origin']} → {lanes[0]['destination']}",
            "detail": f"{lanes[0]['count']} consignments in the last 30 days — the single largest origin.",
            "tone": "info",
        },
        {
            "title": f"Watch quality from {conf[0]['country']}",
            "detail": f"Documents from {conf[0]['country']} average only {conf[0]['avg_confidence'] * 100:.0f}% confidence — "
            "route more of these to manual review.",
            "tone": "warning",
        },
        {
            "title": f"Cleanest source: {conf[-1]['country']}",
            "detail": f"{conf[-1]['country']} averages {conf[-1]['avg_confidence'] * 100:.0f}% confidence — strong candidate for auto-clearance.",
            "tone": "positive",
        },
    ]

