"""Rule-based extraction from OCR text. Missing values are NEVER invented; every uncertain item is flagged."""
import difflib
import json
import re
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data"

# ------------------------------------------------------------------ document type detection
_KEYWORDS = {
    "ecg": ["ecg", "ekg", "electrocardiogram", "qrs", "qtc", "pr interval", "sinus rhythm", "رسم القلب", "تخطيط القلب"],
    "lab": ["reference range", "ref. range", "hemoglobin", "cholesterol", "glucose", "creatinine", "wbc", "rbc", "تحليل", "المعدل الطبيعي", "triglycerides", "hdl", "ldl"],
    "prescription": ["rx", "tab ", "tablet", "capsule", "mg", "sig:", "dispense", "روشتة", "وصفة", "قرص", "كبسولة", "مرة يوميا"],
}


def detect_document_type(text: str) -> tuple[str | None, dict]:
    low = text.lower()
    scores = {k: sum(1 for w in ws if w in low) for k, ws in _KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return (best if scores[best] >= 2 else None), scores


# ------------------------------------------------------------------ laboratory reports
_NUM = r"[-+]?\d+(?:[.,]\d+)?"
_LAB_LINE = re.compile(
    rf"^(?P<name>[A-Za-z][A-Za-z0-9 .()/%\-]{{1,40}}?)\s+(?P<flag>[HL]\s+)?(?P<value>{_NUM})\s*(?P<unit>[A-Za-z%/µμ.^0-9]+(?:/[A-Za-z0-9]+)?)?"
    rf"(?:\s*\(?\s*(?P<lo>{_NUM})\s*[-–to]+\s*(?P<hi>{_NUM})\s*\)?)?\s*$")
_DATE = re.compile(r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b")


def _f(x: str) -> float:
    return float(x.replace(",", "."))


def parse_lab(text: str) -> dict:
    results, warnings = [], []
    for raw in text.splitlines():
        m = _LAB_LINE.match(raw.strip())
        if not m:
            continue
        name = m["name"].strip(" .")
        if len(name) < 2 or name.lower() in {"page", "date", "age", "phone", "tel"}:
            continue
        item = {"test": name, "value": _f(m["value"]), "unit": m["unit"], "reference_low": None, "reference_high": None, "status": "unknown", "source_line": raw.strip()}
        if m["lo"] and m["hi"]:
            lo, hi = _f(m["lo"]), _f(m["hi"])
            if lo < hi:
                item.update(reference_low=lo, reference_high=hi)
                item["status"] = "low" if item["value"] < lo else "high" if item["value"] > hi else "within_range"
        if item["status"] == "unknown":
            item["note"] = "No reference range printed on the report; not compared. Ask your lab/doctor."
        if not m["unit"]:
            item["note"] = (item.get("note", "") + " Unit not detected.").strip()
        results.append(item)
    d = _DATE.search(text)
    if not results:
        warnings.append("No laboratory result lines could be parsed reliably.")
    return {"report_date": d.group(1) if d else None, "results": results, "warnings": warnings,
            "disclaimer": "Compared only with the reference range printed on the report itself. Values are OCR output and must be verified."}


# ------------------------------------------------------------------ ECG printed measurements
_ECG_PATTERNS = {
    "heart_rate_bpm": r"(?:heart\s*rate|\bHR\b|vent(?:ricular)?\s*rate)\s*[:=]?\s*(\d{2,3})\s*(?:bpm)?",
    "pr_interval_ms": r"\bPR(?:\s*interval)?\s*[:=]?\s*(\d{2,3})\s*(?:ms)?",
    "qrs_duration_ms": r"\bQRS(?:\s*(?:duration|dur))?\s*[:=]?\s*(\d{2,3})\s*(?:ms)?",
    "qt_ms": r"\bQT(?!c)\s*[:=]?\s*(\d{3})\s*(?:ms)?",
    "qtc_ms": r"\bQTc\s*[:=]?\s*(\d{3})\s*(?:ms)?",
}
_ECG_PLAUSIBLE = {"heart_rate_bpm": (20, 300), "pr_interval_ms": (60, 400), "qrs_duration_ms": (40, 250), "qt_ms": (200, 700), "qtc_ms": (250, 700)}
ECG_GLOSSARY = {
    "heart_rate_bpm": "Number of heartbeats per minute.",
    "pr_interval_ms": "Time for the electrical signal to travel from the atria to the ventricles.",
    "qrs_duration_ms": "How long ventricular depolarisation takes.",
    "qt_ms": "Time from ventricular depolarisation to repolarisation.",
    "qtc_ms": "QT interval corrected for heart rate.",
}


def parse_ecg(text: str) -> dict:
    found, warnings = {}, []
    for key, pat in _ECG_PATTERNS.items():
        m = re.search(pat, text, re.I)
        if m:
            v = int(m.group(1))
            lo, hi = _ECG_PLAUSIBLE[key]
            if lo <= v <= hi:
                found[key] = {"value": v, "meaning": ECG_GLOSSARY[key]}
            else:
                warnings.append(f"{key}: OCR read {v}, outside the plausible range; ignored.")
    if not found:
        warnings.append("No printed ECG measurements were readable. A photo of a tracing alone cannot give a reliable diagnosis.")
    return {"measurements": found, "warnings": warnings,
            "disclaimer": "Only printed numbers are extracted. No waveform interpretation or diagnosis is performed; ask a cardiologist."}


# ------------------------------------------------------------------ prescriptions
_LEXICON = json.loads((DATA / "cardio_drug_lexicon.json").read_text())["names"]
_DOSE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(mg|mcg|µg|g|ml|iu|units?)\b", re.I)
_FREQ = re.compile(r"(once|twice|three times|four times|\d+\s*(?:x|times)\s*(?:daily|a day|/day)|(?:od|bid|tid|qid|bd|qd)\b|every\s*\d+\s*hours?|daily|at night|morning|مرة يوميا|مرتين يوميا|كل \d+ ساعات?)", re.I)
_DUR = re.compile(r"(?:for\s*)?(\d+\s*(?:days?|weeks?|months?)|لمدة \d+ \S+)", re.I)


def parse_prescription(text: str, line_confidence: float | None = None) -> dict:
    meds, warnings = [], []
    for raw in text.splitlines():
        line = raw.strip()
        if len(line) < 3:
            continue
        words = re.findall(r"[A-Za-z][A-Za-z\-]{3,}", line)
        best, score = None, 0.0
        for w in words:
            cand = difflib.get_close_matches(w.lower(), _LEXICON, n=1, cutoff=0.78)
            if cand:
                s = difflib.SequenceMatcher(None, w.lower(), cand[0]).ratio()
                if s > score:
                    best, score = cand[0], s
        dose, freq, dur = _DOSE.search(line), _FREQ.search(line), _DUR.search(line)
        if not best and not dose:
            continue
        item = {"name": best, "name_match_score": round(score, 2) if best else None, "dosage": dose.group(0) if dose else None,
                "frequency": freq.group(0) if freq else None, "duration": dur.group(1) if dur else None, "source_line": line, "warnings": []}
        if not best:
            item["warnings"].append("Medication name not recognised: do not guess; verify with the prescriber/pharmacist.")
        elif score < 0.95:
            item["warnings"].append(f"Name matched approximately ({score:.0%}); confirm spelling.")
        if best and not dose:
            item["warnings"].append("Dosage missing or illegible.")
        if best and not freq:
            item["warnings"].append("Frequency missing or illegible.")
        if line_confidence is not None and line_confidence < 60:
            item["warnings"].append("Low OCR confidence for this document.")
        meds.append(item)
    if not meds:
        warnings.append("No medications could be extracted. Handwriting is not supported; enter medications manually.")
    return {"medications": meds, "warnings": warnings, "requires_user_confirmation": True,
            "disclaimer": "OCR extraction is NOT verified medical information. Confirm every item before use."}
