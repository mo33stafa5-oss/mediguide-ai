"""Medication safety review: duplicates, missing fields, allergy matches, curated interaction rules, DailyMed lookup.

Honesty notes:
- NLM retired the RxNav Drug Interaction API (2024), so there is no live interaction API here.
- `interactions.json` is a SMALL curated starter list of well-known class warnings; each entry carries a source
  pointer and `needs_reviewer_approval`. It is NOT exhaustive: absence of a warning never means a combination is safe.
- DailyMed label lookup is live (public NLM web service) and returns the official label text sections when reachable."""
import json
import re
from pathlib import Path

import httpx

DATA = Path(__file__).resolve().parents[2] / "data"
_RULES = json.loads((DATA / "interactions.json").read_text())

PHARMACIST_NOTICE = {
    "en": "This review is informational. It does not prescribe, stop, replace or change any medication or dose, and it cannot declare any prescription safe for you. A pharmacist or doctor must verify all medication decisions.",
    "ar": "هذه المراجعة معلوماتية فقط. لا تصف دواءً ولا توقفه ولا تستبدله ولا تغير جرعته، ولا يمكنها اعتبار أي روشتة آمنة لك. يجب أن يراجع الصيدلي أو الطبيب كل القرارات الدوائية.",
}


def _norm(n: str) -> str:
    return re.sub(r"[^a-z]", "", (n or "").lower())


def review(meds: list[dict], allergies: list[str]) -> dict:
    warnings, interactions = [], []
    names = [m for m in meds if m.get("name")]
    seen: dict[str, int] = {}
    for m in names:
        seen[_norm(m["name"])] = seen.get(_norm(m["name"]), 0) + 1
    for k, c in seen.items():
        if c > 1:
            warnings.append({"type": "duplicate", "severity": "warning", "message": f"'{k}' appears {c} times (possible duplicate medication)."})
    for m in meds:
        label = m.get("name") or m.get("source_line", "?")
        if not m.get("name"):
            warnings.append({"type": "unrecognised", "severity": "warning", "message": f"Could not recognise a medication name in: '{label}'."})
            continue
        if not m.get("dosage"):
            warnings.append({"type": "missing_dosage", "severity": "warning", "message": f"{label}: dosage missing."})
        if not m.get("frequency"):
            warnings.append({"type": "missing_frequency", "severity": "info", "message": f"{label}: frequency missing."})
        for w in m.get("warnings", []):
            if "OCR" in w or "matched" in w:
                warnings.append({"type": "uncertain_ocr", "severity": "warning", "message": f"{label}: {w}"})
        for a in allergies:
            if a and (_norm(a) in _norm(m["name"]) or _norm(m["name"]) in _norm(a)):
                warnings.append({"type": "allergy", "severity": "critical", "message": f"{label} matches your recorded allergy '{a}'. Contact your doctor/pharmacist before taking it."})
    present = {_norm(m["name"]) for m in names}
    for rule in _RULES["rules"]:
        a = [d for d in rule["group_a"] if _norm(d) in present]
        b = [d for d in rule["group_b"] if _norm(d) in present]
        if a and b:
            interactions.append({"drugs": sorted(set(a + b)), "severity": rule["severity"], "summary": rule["summary"], "source": rule["source"], "curated": True})
    return {"warnings": warnings, "interactions": interactions,
            "coverage_note": _RULES["_note"], "pharmacist_notice": PHARMACIST_NOTICE}


def dailymed_lookup(drug_name: str, timeout: float = 10.0) -> dict:
    """Search DailyMed (NLM) for a label and return the setid + title. Returns an explicit unavailable status on failure."""
    try:
        r = httpx.get("https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json", params={"drug_name": drug_name, "pagesize": 3}, timeout=timeout)
        r.raise_for_status()
        rows = r.json().get("data", [])
    except Exception as e:
        return {"status": "unavailable", "reason": type(e).__name__, "source": "DailyMed (NLM)"}
    return {"status": "ok", "source": "DailyMed (NLM)", "labels": [
        {"title": x["title"], "setid": x["setid"], "published": x.get("published_date"),
         "url": f"https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid={x['setid']}"} for x in rows]}
