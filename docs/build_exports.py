"""Builds the combined PDF/DOCX. Mermaid blocks are replaced with their rendered PNG (validated by mermaid-cli)."""
import re, subprocess
from pathlib import Path
R = Path(__file__).resolve().parents[1]; A = R / "docs/academic"; E = R / "docs/exports"; E.mkdir(exist_ok=True)
order = ["00_README", "01_introduction_requirements", "02_analysis_design", "03_frontend_backend_libraries", "04_ai_gemini_rag", "05_machine_learning",
         "06_ocr_documents_prescriptions", "07_api_security", "08_testing_install_deploy", "09_limitations_future_glossary_references", "EXAMINATION_STUDY_GUIDE"]
parts = [(A / f"{n}.md").read_text() for n in order] + [(R / "docs/presentation/PRESENTER_SPEAKER_NOTES.md").read_text()]
md = "\n\n".join(parts)
def img(m):
    stem = re.search(r"docs/diagrams/(\S+?)\.mmd", md[m.end():m.end() + 200])
    return m.group(0)
# replace each mermaid block (followed by its Source line naming the file) with the PNG
def repl(m):
    block, src = m.group(1), m.group(2)
    return f"![]({R}/docs/diagrams/png/{src}.png){{width=100%}}\n\n*Diagram source: docs/diagrams/{src}.mmd*"
md = re.sub(r"```mermaid\n(.*?)```\n\n\*\(Source: `docs/diagrams/([\w]+)\.mmd`.*?\)\*", repl, md, flags=re.S)
assert "```mermaid" not in md
(E / "_combined.md").write_text(md)
cmd = ["pandoc", str(E / "_combined.md"), "-o", str(E / "MediGuide_AI_Complete_Documentation.docx"), "--toc", "--toc-depth=2", "--from", "gfm+pipe_tables", "--resource-path", str(R),
       "-M", "title=MediGuide AI — Complete Documentation", "-M", "author=MediGuide AI project", "-M", "lang=en"]
subprocess.run(cmd, check=True)
subprocess.run(["soffice", "--headless", "--convert-to", "pdf", str(E / "MediGuide_AI_Complete_Documentation.docx"), "--outdir", str(E)], check=True, capture_output=True, timeout=600)
(E / "_combined.md").unlink()
print({p.name: p.stat().st_size for p in E.iterdir()})
