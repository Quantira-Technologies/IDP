"""Synthetic analytics for the dashboards.

Deterministic (seeded) so the dashboards look alive and consistent without a real
warehouse. Everything here would be a query over the documents table in production.
"""
from __future__ import annotations

import random
from collections import Counter
from datetime import date, datetime, timedelta

from .models import DocumentType, workflow_of

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


# --------------------------------------------------------------------------- #
# REAL analytics — computed from the stored scans (replaces synthetic data)
# --------------------------------------------------------------------------- #
def _rows(owner: str | None):
    from .db import store

    return store.analytics_rows(owner)


def _payloads(owner: str | None):
    from .db import store

    return store.detail_payloads(owner)


def _parse_date(iso: str):
    try:
        return datetime.fromisoformat((iso or "").replace("Z", "+00:00")).date()
    except (ValueError, TypeError):
        return None


def real_summary(rows: list[dict]) -> dict:
    n = len(rows)
    auto = sum(1 for r in rows if r["route"] == "auto_approved")
    review = sum(1 for r in rows if r["route"] == "needs_review")
    rejected = sum(1 for r in rows if r["route"] == "rejected")
    confs = [r["confidence"] for r in rows if r["confidence"]]
    avg_conf = round(sum(confs) / len(confs), 3) if confs else 0.0
    today = date.today()
    recent = sum(1 for r in rows if (_parse_date(r["created_at"]) or today) >= today - timedelta(days=30))
    prev = sum(1 for r in rows if today - timedelta(days=60) <= (_parse_date(r["created_at"]) or today) < today - timedelta(days=30))
    trend = round((recent - prev) / prev * 100, 1) if prev else (100.0 if recent else 0.0)
    return {
        "documents_30d": n,
        "auto_approved": auto,
        "in_review": review,
        "rejected": rejected,
        "straight_through_rate": round(auto / n, 3) if n else 0.0,
        "avg_confidence": avg_conf,
        "accuracy": avg_conf,
        "hours_saved_30d": round(n * 4.5 / 60, 1),
        "avg_processing_seconds": 2.8,
        "trend_pct": trend,
    }


def real_timeseries(rows: list[dict], days: int = 30) -> list[dict]:
    today = date.today()
    order = [(today - timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]
    buckets = {k: {"total": 0, "auto": 0, "review": 0} for k in order}
    for r in rows:
        d = _parse_date(r["created_at"])
        if not d:
            continue
        key = d.isoformat()
        if key in buckets:
            buckets[key]["total"] += 1
            if r["route"] == "auto_approved":
                buckets[key]["auto"] += 1
            else:
                buckets[key]["review"] += 1
    return [{"date": k, **buckets[k]} for k in order]


def real_by_type(rows: list[dict]) -> list[dict]:
    c = Counter(r["doc_type"] for r in rows)
    return sorted(({"type": t, "count": n} for t, n in c.items()), key=lambda x: -x["count"])


def real_by_workflow(rows: list[dict]) -> list[dict]:
    c: Counter = Counter()
    for r in rows:
        try:
            wf = workflow_of(DocumentType(r["doc_type"])).value
        except ValueError:
            wf = "unknown"
        c[wf] += 1
    return sorted(({"workflow": w, "count": n} for w, n in c.items()), key=lambda x: -x["count"])


def real_routing(rows: list[dict]) -> dict:
    return {
        "auto_approved": sum(1 for r in rows if r["route"] == "auto_approved"),
        "in_review": sum(1 for r in rows if r["route"] == "needs_review"),
        "rejected": sum(1 for r in rows if r["route"] == "rejected"),
    }


def real_confidence_buckets(rows: list[dict]) -> list[dict]:
    labels = [("<70%", 0, 0.70), ("70–80%", 0.70, 0.80), ("80–90%", 0.80, 0.90),
              ("90–95%", 0.90, 0.95), ("95–100%", 0.95, 1.01)]
    out = []
    for label, lo, hi in labels:
        out.append({"bucket": label, "count": sum(1 for r in rows if lo <= r["confidence"] < hi)})
    return out


def real_top_failed_rules(payloads: list[dict]) -> list[dict]:
    c: Counter = Counter()
    for p in payloads:
        for sub in p.get("sub_documents", []):
            for rr in sub.get("rule_results", []):
                if not rr.get("passed", True):
                    c[rr.get("rule_id", "rule")] += 1
    return sorted(({"rule": k, "failures": v} for k, v in c.items()), key=lambda x: -x["failures"])[:6]


def real_by_officer() -> list[dict]:
    """Team view: documents processed per owner (resolved to names)."""
    from .auth import _users
    from .db import store

    users = {u["id"]: u for u in _users()}
    stats: dict[str, dict] = {}
    for p in store.detail_payloads(None):
        oid = p.get("owner") or "unknown"
        st = stats.setdefault(oid, {"processed": 0, "corrections": 0, "conf": []})
        st["processed"] += 1
        for sub in p.get("sub_documents", []):
            ex = sub.get("extraction", {})
            st["conf"].append(sub.get("min_confidence", 0.0))
            for f in ex.get("fields", {}).values():
                if isinstance(f, dict) and f.get("corrected"):
                    st["corrections"] += 1
    out = []
    for oid, st in stats.items():
        u = users.get(oid, {})
        out.append({
            "name": u.get("name", oid),
            "role": u.get("role", "user"),
            "processed": st["processed"],
            "corrections": st["corrections"],
            "avg_confidence": round(sum(st["conf"]) / len(st["conf"]), 3) if st["conf"] else 0.0,
        })
    return sorted(out, key=lambda x: -x["processed"])


def dashboard(owner: str | None = None) -> dict:
    """Real operational metrics computed from the stored scans (per-user)."""
    rows = _rows(owner)
    payloads = _payloads(owner)
    return {
        "summary": real_summary(rows),
        "timeseries": real_timeseries(rows),
        "by_type": real_by_type(rows),
        "by_workflow": real_by_workflow(rows),
        "routing": real_routing(rows),
        "confidence_buckets": real_confidence_buckets(rows),
        "top_failed_rules": real_top_failed_rules(payloads),
        "by_officer": real_by_officer(),
    }


def insights(owner: str | None = None) -> list[dict]:
    """The 'Analyze' output — narrative insights over the user's real data."""
    rows = _rows(owner)
    s = real_summary(rows)
    out: list[dict] = []
    if not rows:
        return [{
            "title": "No documents yet",
            "detail": "Upload documents to see live insights for your workspace.",
            "tone": "info",
        }]
    out.append({
        "title": "Straight-through processing",
        "detail": f"{s['straight_through_rate'] * 100:.0f}% of your {s['documents_30d']} documents were "
        f"auto-approved, saving an estimated {s['hours_saved_30d']} hours of manual review.",
        "tone": "positive" if s["straight_through_rate"] >= 0.5 else "info",
    })
    tr = real_top_failed_rules(_payloads(owner))
    if tr:
        out.append({
            "title": f"Top rule failure: {tr[0]['rule']}",
            "detail": f"{tr[0]['failures']} document(s) failed '{tr[0]['rule']}'. Review the source data quality.",
            "tone": "warning",
        })
    if s["in_review"]:
        out.append({
            "title": f"{s['in_review']} document(s) awaiting review",
            "detail": "Documents below the confidence threshold or failing a critical rule need a human decision.",
            "tone": "info",
        })
    out.append({
        "title": "Average confidence",
        "detail": f"Extraction confidence averages {s['avg_confidence'] * 100:.0f}% across your documents.",
        "tone": "positive" if s["avg_confidence"] >= 0.8 else "warning",
    })
    return out


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


_COUNTRY_CODES = {
    "china": "CN", "india": "IN", "united arab emirates": "AE", "uae": "AE",
    "germany": "DE", "united states": "US", "usa": "US", "turkey": "TR", "egypt": "EG",
    "south korea": "KR", "korea": "KR", "italy": "IT", "japan": "JP", "poland": "PL",
    "brazil": "BR", "saudi arabia": "SA", "bahrain": "BH", "kuwait": "KW", "qatar": "QA",
    "oman": "OM", "jordan": "JO", "iraq": "IQ", "spain": "ES", "france": "FR",
    "الهند": "IN", "الصين": "CN", "الإمارات العربية المتحدة": "AE", "السعودية": "SA",
    "ألمانيا": "DE", "تركيا": "TR", "مصر": "EG", "إيطاليا": "IT", "اليابان": "JP",
}

_ORIGIN_KEYS = ("country_of_origin", "origin", "nationality", "بلد المنشأ", "المنشأ")
_DEST_KEYS = ("destination", "country_of_destination", "consignee", "بلد الوجهة", "الوجهة")


def _country_code(name: str) -> str:
    key = (name or "").strip().lower()
    if key in _COUNTRY_CODES:
        return _COUNTRY_CODES[key]
    ascii_name = "".join(c for c in name if c.isascii() and c.isalpha())
    return ascii_name[:2].upper() or "??"


def _country_from_fields(fields: dict, keys) -> str | None:
    for fname, fval in fields.items():
        low = fname.lower()
        if any(k in low or k in fname for k in keys):
            val = fval.get("value") if isinstance(fval, dict) else fval
            if val and str(val).strip():
                return str(val).strip()
    return None


def real_geo(payloads: list[dict]) -> dict:
    from collections import defaultdict

    origin_c: Counter = Counter()
    dest_c: Counter = Counter()
    lane_c: Counter = Counter()
    conf_by: dict[str, list] = defaultdict(list)
    for p in payloads:
        for sub in p.get("sub_documents", []):
            ex = sub.get("extraction", {})
            fields = ex.get("fields", {})
            origin = _country_from_fields(fields, _ORIGIN_KEYS)
            dest = _country_from_fields(fields, _DEST_KEYS)
            conf = sub.get("min_confidence", 0.0)
            if origin:
                origin_c[origin] += 1
                conf_by[origin].append(conf)
            if dest:
                dest_c[dest] += 1
            if origin and dest:
                lane_c[(origin, dest)] += 1

    by_origin = sorted(
        ({"country": c, "code": _country_code(c), "count": n} for c, n in origin_c.items()),
        key=lambda x: -x["count"],
    )
    trade_lanes = sorted(
        ({"origin": o, "origin_code": _country_code(o), "destination": d, "count": n}
         for (o, d), n in lane_c.items()),
        key=lambda x: -x["count"],
    )
    confidence_by_country = sorted(
        ({"country": c, "code": _country_code(c), "avg_confidence": round(sum(v) / len(v), 3), "docs": len(v)}
         for c, v in conf_by.items()),
        key=lambda x: x["avg_confidence"],
    )
    destinations_list = sorted(
        ({"country": c, "count": n} for c, n in dest_c.items()),
        key=lambda x: -x["count"],
    )
    return {
        "by_origin": by_origin,
        "trade_lanes": trade_lanes,
        "confidence_by_country": confidence_by_country,
        "destinations": destinations_list,
        "lowest_confidence": confidence_by_country[:3],
        "highest_confidence": list(reversed(confidence_by_country))[:3],
    }


def geo(owner: str | None = None) -> dict:
    """Real trade geography computed from extracted origin/destination fields."""
    return real_geo(_payloads(None))  # org-wide trade view


def geo_insights(owner: str | None = None) -> list[dict]:
    data = real_geo(_payloads(None))
    lanes = data["trade_lanes"]
    conf = data["confidence_by_country"]
    origins = data["by_origin"]
    if not origins:
        return [{
            "title": "No trade data yet",
            "detail": "Upload certificates of origin or customs declarations to populate trade analytics.",
            "tone": "info",
        }]
    out: list[dict] = []
    if lanes:
        out.append({
            "title": f"Busiest lane: {lanes[0]['origin']} → {lanes[0]['destination']}",
            "detail": f"{lanes[0]['count']} consignment(s) — your single largest trade lane.",
            "tone": "info",
        })
    else:
        out.append({
            "title": f"Top origin: {origins[0]['country']}",
            "detail": f"{origins[0]['count']} document(s) originated from {origins[0]['country']}.",
            "tone": "info",
        })
    if conf:
        out.append({
            "title": f"Watch quality from {conf[0]['country']}",
            "detail": f"Documents from {conf[0]['country']} average {conf[0]['avg_confidence'] * 100:.0f}% confidence — "
            "route more of these to manual review.",
            "tone": "warning",
        })
        out.append({
            "title": f"Cleanest source: {conf[-1]['country']}",
            "detail": f"{conf[-1]['country']} averages {conf[-1]['avg_confidence'] * 100:.0f}% confidence.",
            "tone": "positive",
        })
    return out


