"""Vercel Python entrypoint: exposes the FastAPI app (see vercel.json rewrites)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from backend.app.main import app  # noqa: E402,F401
