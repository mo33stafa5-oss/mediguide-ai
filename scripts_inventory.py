"""Verifies declared dependencies against actual imports (Rule 1: actual libraries only)."""
import ast, json, re, sys
from pathlib import Path
ROOT = Path(__file__).parent

# ---- Python
pymods: dict[str, set[str]] = {}
for base in ("backend", "ml", "api"):
    for f in (ROOT / base).rglob("*.py"):
        if ".venv" in f.parts: continue
        for n in ast.walk(ast.parse(f.read_text())):
            names = [a.name for a in n.names] if isinstance(n, ast.Import) else ([n.module] if isinstance(n, ast.ImportFrom) and n.module and n.level == 0 else [])
            for m in names:
                pymods.setdefault(m.split(".")[0], set()).add(str(f.relative_to(ROOT)))
IMPORT_NAME = {"scikit-learn": "sklearn", "pillow": "PIL", "pydantic-settings": "pydantic_settings", "python-multipart": "multipart",
               "opencv-python-headless": "cv2", "google-genai": "google", "pyjwt": "jwt"}
declared = {}
for fn in ("backend/requirements.txt", "backend/requirements-ocr.txt", "requirements-dev.txt"):
    for l in (ROOT / fn).read_text().splitlines():
        m = re.match(r"([A-Za-z0-9_.\-]+)(?:\[.*\])?==([\w.]+)", l.strip())
        if m: declared[m[1].lower()] = (m[2], fn)
py_report = {}
for name, (ver, fn) in sorted(declared.items()):
    imp = IMPORT_NAME.get(name, name.replace("-", "_"))
    files = sorted(pymods.get(imp, []))
    py_report[name] = {"version": ver, "declared_in": fn, "import_name": imp, "used_in": files}

# ---- npm
pkg = json.loads((ROOT / "package.json").read_text())
srcs = [p for d in ("app", "components", "lib", "tests/e2e") for p in (ROOT / d).rglob("*.ts*")] + [ROOT / p for p in ("proxy.ts", "next.config.ts", "playwright.config.ts", "eslint.config.mjs")]
text = {str(p.relative_to(ROOT)): p.read_text() for p in srcs if p.exists()}
lock = json.loads((ROOT / "package-lock.json").read_text())["packages"]
npm_report = {}
for sect in ("dependencies", "devDependencies"):
    for name, spec in pkg[sect].items():
        installed = lock.get(f"node_modules/{name}", {}).get("version")
        files = sorted(f for f, t in text.items() if re.search(rf"""['"]{re.escape(name)}(/[^'"]*)?['"]""", t))
        npm_report[name] = {"section": sect, "version": installed, "used_in": files}
json.dump({"python": py_report, "npm": npm_report}, open(ROOT / "docs_inventory.json", "w"), indent=1)
for k, v in {**{"py:" + k: v for k, v in py_report.items()}, **{"npm:" + k: v for k, v in npm_report.items()}}.items():
    if not v["used_in"]: print("UNUSED-IMPORT:", k, v.get("version"))
