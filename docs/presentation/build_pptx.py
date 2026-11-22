"""Builds the editable PowerPoint from REAL data (evaluation.json) and REAL screenshots/diagrams."""
import json
from pathlib import Path
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt
from PIL import Image

R = Path(__file__).resolve().parents[2]
SS, DG = R / "docs/presentation/screenshots", R / "docs/diagrams/png"
ev = json.loads((R / "ml/reports/evaluation.json").read_text())
BLUE, CYAN, NAVY, SOFT, WHITE, GREY = (RGBColor(0x16, 0x77, 0xE8), RGBColor(0x16, 0xC5, 0xD5), RGBColor(0x10, 0x2A, 0x56), RGBColor(0xEA, 0xF3, 0xFF), RGBColor(255, 255, 255), RGBColor(0x5B, 0x6B, 0x8A))
prs = Presentation(); prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
blank = prs.slide_layouts[6]
notes = {}

def box(s, x, y, w, h, fill=None, line=None, shape=MSO_SHAPE.ROUNDED_RECTANGLE):
    sh = s.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if fill is None: sh.fill.background()
    else: sh.fill.solid(); sh.fill.fore_color.rgb = fill
    if line is None: sh.line.fill.background()
    else: sh.line.color.rgb = line
    sh.shadow.inherit = False
    return sh

def text(s, x, y, w, h, t, size=18, bold=False, color=NAVY, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)); tf = tb.text_frame; tf.word_wrap = True; tf.vertical_anchor = anchor
    for i, line in enumerate(t if isinstance(t, list) else [t]):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph(); p.alignment = align
        r = p.add_run(); r.text = line; r.font.size = Pt(size); r.font.bold = bold; r.font.color.rgb = color; r.font.name = "Segoe UI"
    return tb

def bullets(s, x, y, w, items, size=20, gap=0.62, color=NAVY):
    for i, it in enumerate(items):
        dot = box(s, x, y + i * gap + 0.12, 0.16, 0.16, CYAN, shape=MSO_SHAPE.OVAL)
        text(s, x + 0.3, y + i * gap, w - 0.3, gap, it, size, color=color)

def slide(title, note, n):
    s = prs.slides.add_slide(blank)
    box(s, 0, 0, 13.333, 1.15, NAVY, shape=MSO_SHAPE.RECTANGLE)
    box(s, 0, 1.15, 13.333, 0.07, CYAN, shape=MSO_SHAPE.RECTANGLE)
    text(s, 0.6, 0.18, 11, 0.85, title, 32, True, WHITE, anchor=MSO_ANCHOR.MIDDLE)
    s.shapes.add_picture(str(SS / "logo.png"), Inches(12.3), Inches(0.2), Inches(0.75), Inches(0.75))
    text(s, 0.6, 7.05, 9, 0.35, "MediGuide AI · Educational and research tool — not a diagnosis · Emergency (Egypt): 123", 11, color=GREY)
    text(s, 12.2, 7.05, 0.8, 0.35, str(n), 11, color=GREY, align=PP_ALIGN.RIGHT)
    s.notes_slide.notes_text_frame.text = note
    return s

def pic(s, path, x, y, maxw, maxh):
    w, h = Image.open(path).size; k = min(maxw / w, maxh / h)
    s.shapes.add_picture(str(path), Inches(x + (maxw - w * k) / 2), Inches(y), Inches(w * k), Inches(h * k))

def label(s, x, y, t, tone=CYAN):
    b = box(s, x, y, 2.6, 0.38, tone); tf = b.text_frame; tf.text = t; p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    p.runs[0].font.size = Pt(12); p.runs[0].font.bold = True; p.runs[0].font.color.rgb = WHITE

# 1 Title
s = prs.slides.add_slide(blank); box(s, 0, 0, 13.333, 7.5, NAVY, shape=MSO_SHAPE.RECTANGLE); box(s, 0, 5.4, 13.333, 0.1, CYAN, shape=MSO_SHAPE.RECTANGLE)
s.shapes.add_picture(str(SS / "logo.png"), Inches(0.9), Inches(1.3), Inches(1.9), Inches(1.9))
text(s, 3.1, 1.25, 9.5, 1.2, "MediGuide AI", 66, True, WHITE); text(s, 3.1, 2.45, 9.5, 0.7, "AI for a Healthier Tomorrow", 30, False, CYAN)
text(s, 3.1, 3.2, 9.5, 0.6, "معلومات أوضح .. قرارات أفضل .. صحة أسهل", 24, False, WHITE)
text(s, 0.9, 5.8, 11.5, 1.2, ["Full-stack healthcare AI platform for cardiovascular education", "University project · Python · Machine Learning · OCR · RAG · Supabase"], 18, False, SOFT)
s.notes_slide.notes_text_frame.text = "Title slide. Introduce the project name and the Arabic slogan."
# 2 Introduction
s = slide("Introduction", "Introduce what the platform is and stress it is educational.", 2)
bullets(s, 0.7, 1.7, 6.2, ["Bilingual (Arabic RTL / English LTR) web platform", "Cardiovascular health education", "Private workspace for every patient", "Chat · risk model · documents · medication review", "Educational — never diagnoses or prescribes"], 22, 0.85)
pic(s, SS / "01_landing_ar.png", 7.2, 1.7, 5.7, 4.8); label(s, 7.2, 6.5, "Real screenshot")
# 3 Problem
s = slide("Problem Statement", "The problem: patients cannot understand reports; generic AI is unsafe and unsourced.", 3)
for i, (h, d) in enumerate([("Hard to understand", "Lab values, ECG printouts and prescriptions are opaque to patients"), ("Unsafe AI advice", "General chatbots hallucinate and give no sources or emergency protocol"), ("Privacy risk", "Medical files shared with tools that lack tenant isolation"), ("Language gap", "Few clear Arabic, source-cited explanations")]):
    x = 0.7 + (i % 2) * 6.1; y = 1.7 + (i // 2) * 2.4; box(s, x, y, 5.8, 2.1, SOFT); box(s, x, y, 0.12, 2.1, CYAN, shape=MSO_SHAPE.RECTANGLE)
    text(s, x + 0.35, y + 0.2, 5.2, 0.5, h, 24, True, BLUE); text(s, x + 0.35, y + 0.85, 5.2, 1.1, d, 18)
# 4 Objectives
s = slide("Project Objectives", "Six objectives; each maps to implemented modules.", 4)
bullets(s, 0.7, 1.6, 12, ["Secure multi-tenant platform: database-enforced privacy (RLS)", "Safe medical chat with emergency handling and cited sources", "Real scikit-learn model with honest evaluation", "OCR of printed lab, ECG and prescription values with uncertainty flags", "Medication-safety review with human confirmation", "Tested, deployable codebase and full academic documentation"], 22, 0.85)
# 5 Solution
s = slide("Proposed Solution", "One platform, five cooperating modules on one secure database.", 5)
for i, (h, d) in enumerate([("Chat + RAG", "Gemini answers with approved sources"), ("Risk model", "UCI Cleveland · scikit-learn"), ("Documents", "Upload · OCR · uncertainty"), ("Medication safety", "Duplicates · allergies · interactions"), ("Privacy core", "RLS · private storage · consent")]):
    x = 0.55 + i * 2.5; box(s, x, 2.2, 2.3, 3.3, SOFT, BLUE); text(s, x + 0.1, 2.5, 2.1, 0.9, h, 20, True, BLUE, PP_ALIGN.CENTER); text(s, x + 0.1, 3.5, 2.1, 1.6, d, 16, False, NAVY, PP_ALIGN.CENTER)
text(s, 0.7, 5.9, 12, 0.6, "Every result carries a disclaimer: educational information, not a diagnosis.", 18, True, NAVY, PP_ALIGN.CENTER)
# 6 Features
s = slide("Main Features (real screenshots)", "Show the dashboard and mobile view; both are real captures of the running app.", 6)
pic(s, SS / "03_dashboard.png", 0.5, 1.5, 7.9, 5.2); pic(s, SS / "11_mobile_dashboard.png", 8.9, 1.5, 3.9, 5.3)
# 7 Architecture
s = slide("System Architecture", "Browser to Next.js to FastAPI to Supabase; Gemini/DailyMed external; OCR in a Docker worker. Vercel deployment is prepared, not done.", 7)
pic(s, DG / "01_architecture.png", 0.5, 1.45, 12.3, 5.4)
# 8 Stack
s = slide("Technology Stack (verified)", "Only libraries actually installed and imported are listed.", 8)
for i, (h, items) in enumerate([("Frontend", ["Next.js 16.4 · React 19", "TypeScript · Tailwind 4", "React Hook Form · Zod", "Recharts · Lucide"]), ("Backend", ["Python 3.12 · FastAPI", "Pydantic · httpx", "supabase-py · google-genai", "pypdf · Pillow"]), ("ML & OCR", ["scikit-learn · pandas", "NumPy · joblib", "OpenCV · Tesseract", "matplotlib (reports)"]), ("Data & QA", ["Supabase: Postgres, Auth, Storage", "pgvector · RLS", "pytest · Playwright", "ESLint"])]):
    x = 0.5 + i * 3.15; box(s, x, 1.7, 3.0, 4.8, SOFT); text(s, x + 0.2, 1.85, 2.6, 0.5, h, 22, True, BLUE)
    for j, it in enumerate(items): text(s, x + 0.2, 2.6 + j * 0.9, 2.65, 0.8, it, 16)
# 9 Python & ML
s = slide("Python and Machine Learning", "Why Python and scikit-learn; pipeline stages; no leakage.", 9)
bullets(s, 0.7, 1.6, 6.3, ["Why Python: ML + OCR + API in one language", "UCI Cleveland: 303 patients, 13 features", "Impute · one-hot · scale inside a Pipeline", "Stratified 80/20 split (242 / 61)", "GridSearchCV on training data only", "Test set used once; model chosen by CV"], 20, 0.8)
box(s, 7.3, 1.8, 5.6, 2.2, SOFT); text(s, 7.5, 1.95, 5.2, 1.9, ["Load → clean → Pipeline", "→ GridSearchCV (train only)", "→ test once → save joblib"], 18, True, BLUE); text(s, 7.3, 4.4, 5.6, 1.5, "Trained offline: python -m ml.train. The API only loads the saved joblib pipeline.", 18, True, BLUE)
# 10 ML results (real)
s = slide("ML Workflow and ACTUAL Results", "Read the table from evaluation.json. Emphasise small test set and honest selection rule.", 10)
rows = [("Model", "Acc", "Prec", "Rec", "F1", "ROC-AUC", "CV AUC")] + [(n, *(f"{r['test'][k]:.3f}" for k in ("accuracy", "precision", "recall", "f1", "roc_auc")), f"{r['cv_roc_auc_mean_train_only']:.3f}") for n, r in ev["results"].items()]
tbl = s.shapes.add_table(len(rows), 7, Inches(0.6), Inches(1.6), Inches(7.6), Inches(2.6)).table
for i, row in enumerate(rows):
    for j, v in enumerate(row):
        c = tbl.cell(i, j); c.text = v; p = c.text_frame.paragraphs[0]; p.runs[0].font.size = Pt(13); p.runs[0].font.bold = (i == 0 or row[0] == ev["selected_model"]); p.runs[0].font.color.rgb = WHITE if i == 0 else NAVY
        c.fill.solid(); c.fill.fore_color.rgb = BLUE if i == 0 else (SOFT if row[0] != ev["selected_model"] else RGBColor(0xC9, 0xEE, 0xF2))
tbl.columns[0].width = Inches(2.4)
text(s, 0.6, 4.4, 7.6, 2.4, [f"Selected (by CV on training split): {ev['selected_model']}", f"Dataset {ev['dataset']['rows']} rows · train {ev['dataset']['train_rows']} / test {ev['dataset']['test_rows']}", "61 test patients: model differences are within noise", "Single site, no external validation: research score, not a diagnosis"], 16)
pic(s, R / "ml/reports/roc_curves.png", 8.4, 1.5, 4.6, 4.4); label(s, 8.7, 6.0, "Generated by the training run")
# 11 Chat and RAG
s = slide("AI Chat and RAG", "Explain the chat flow and RAG. State clearly that live Gemini has not been tested (no key) and the knowledge base is empty.", 11)
pic(s, DG / "05_rag_workflow.png", 0.5, 1.5, 7.4, 5.3)
bullets(s, 8.2, 1.7, 4.9, ["Emergency regex → 123 warning first", "Consent before data goes to Gemini", "Approved-only retrieval (pgvector)", "Citations: name · URL · dates"], 17, 0.75)
box(s, 8.2, 4.9, 4.7, 1.7, RGBColor(0xFF, 0xF3, 0xCD), RGBColor(0xC7, 0x77, 0x00)); text(s, 8.35, 4.95, 4.4, 1.6, ["Status: pipeline built and tested with a test double.", "Not yet run against live Gemini; knowledge base awaits real approved sources."], 14, False, RGBColor(0x7A, 0x45, 0x00))
# 12 Documents
s = slide("Medical Document Processing", "Show the real OCR screenshot. X-ray and ECG waveform analysis are NOT implemented.", 12)
pic(s, SS / "06_documents_ocr.png", 0.4, 1.45, 7.7, 5.3)
bullets(s, 8.4, 1.6, 4.6, ["Magic-byte validation, private buckets", "OpenCV + Tesseract, confidence shown", "Lab values vs the report's printed range", "ECG: printed numbers only", "Prescription: human confirmation", "X-ray: metadata only, no diagnosis"], 16, 0.72)
label(s, 8.6, 6.1, "Not built: X-ray / ECG AI", RGBColor(0xC7, 0x77, 0x00))
# 13 DB & security
s = slide("Database and Security", "RLS is the core; admins cannot read patient private rows.", 13)
pic(s, DG / "03_erd.png", 0.4, 1.4, 6.6, 5.5)
bullets(s, 7.3, 1.6, 5.7, ["Row Level Security on all 12 tables", "User JWT used for DB calls", "Private storage + 120 s signed URLs", "Role-escalation trigger", "Rate limits · audit log · consent", "Account export and deletion"], 18, 0.75)
text(s, 7.3, 6.2, 5.7, 0.7, "Gaps: no CSP, per-instance rate limit, no MFA, retention job.", 14, False, GREY)
# 14 Testing
s = slide("Testing (executed results)", "Quote only these numbers. Mention what is not covered.", 14)
for i, (n, h, d) in enumerate([("59", "backend tests passed", "unit · ML · API · RLS · upload/OCR · RAG"), ("16", "Playwright E2E passed", "RTL/LTR · real email verification · upload→OCR"), ("0", "lint errors", "11 warnings · production build passes"), ("56+3", "in Vercel-like clean env", "3 OCR tests skipped (no Tesseract)")]):
    x = 0.6 + i * 3.1; box(s, x, 1.8, 2.9, 3.4, SOFT); text(s, x, 2.0, 2.9, 1.2, n, 54, True, BLUE, PP_ALIGN.CENTER); text(s, x + 0.1, 3.3, 2.7, 0.7, h, 18, True, NAVY, PP_ALIGN.CENTER); text(s, x + 0.15, 4.0, 2.6, 1.0, d, 13, False, GREY, PP_ALIGN.CENTER)
text(s, 0.6, 5.6, 12.1, 1.2, "Not tested: live Gemini, live DailyMed, the Vercel runtime, noisy phone photos, Arabic OCR accuracy, adversarial prompts.", 17, True, RGBColor(0x9A, 0x5B, 0x00))
# 15 Limits
s = slide("Limitations and Future Work", "Be upfront. These are the first questions a professor will ask.", 15)
text(s, 0.6, 1.5, 6, 0.5, "Limitations", 24, True, BLUE); bullets(s, 0.6, 2.1, 6, ["Educational; not clinically validated", "303 patients, one hospital, 1980s", "No X-ray / ECG-waveform analysis", "Tiny curated interaction list", "Not deployed; live Gemini untested"], 17, 0.78)
text(s, 7.0, 1.5, 6, 0.5, "Future work", 24, True, BLUE); bullets(s, 7.0, 2.1, 6, ["Real WHO/AHA sources + review expiry", "Public-dataset X-ray / ECG research models", "Licensed interaction data, class allergies", "Calibration, external validation, clinicians", "MFA, CSP, global rate limit, retention job"], 17, 0.78)
# 16 Conclusion
s = prs.slides.add_slide(blank); box(s, 0, 0, 13.333, 7.5, NAVY, shape=MSO_SHAPE.RECTANGLE); box(s, 0, 5.5, 13.333, 0.1, CYAN, shape=MSO_SHAPE.RECTANGLE)
s.shapes.add_picture(str(SS / "logo.png"), Inches(0.9), Inches(0.9), Inches(1.4), Inches(1.4))
text(s, 2.6, 0.9, 10, 1, "Conclusion and Questions", 44, True, WHITE)
bullets(s, 0.9, 2.7, 11.5, ["A secure, tested, bilingual platform exists end to end", "Real ML results, reported honestly", "Safety first: emergency handling, consent, no diagnosis", "Next: live Gemini, real sources, deployment, clinical validation"], 22, 0.7, WHITE)
text(s, 0.9, 5.9, 11.5, 0.8, "Thank you — Questions?   شكرًا — هل من أسئلة؟", 28, True, CYAN)
s.notes_slide.notes_text_frame.text = "Summarise, then invite questions."
prs.save(R / "docs/presentation/MediGuide_AI_University_Presentation.pptx"); print("slides:", len(prs.slides))
