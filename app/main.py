"""Piano Scribe Web 服务入口。"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .api import router

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="Piano Scribe — 钢琴录音转谱", version=__version__)
app.include_router(router)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(str(STATIC_DIR / "index.html"))
