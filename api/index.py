"""
Vercel serverless entry: ASGI app mounted at /api (compile, run, health, etc.).
Local development continues to use: uvicorn main:app from the backend/ folder.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
_backend = _root / "backend"
sys.path.insert(0, str(_backend))
os.environ.setdefault("VERCEL", "1")

from fastapi import FastAPI  # noqa: E402
from main import app  # noqa: E402 — backend/main.py

root = FastAPI()
root.mount("/api", app)

from mangum import Mangum  # noqa: E402

handler = Mangum(root, lifespan="off")
