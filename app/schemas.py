"""API 数据结构。"""
from __future__ import annotations

from pydantic import BaseModel


class EngineInfo(BaseModel):
    name: str
    display_name: str
    requires_ml: bool


class EnginesResponse(BaseModel):
    engines: dict[str, EngineInfo]
    default: str


class JobStatus(BaseModel):
    job_id: str
    status: str              # queued | running | done | failed
    error: str | None = None
    engine: str | None = None
    duration: float | None = None   # 音频时长（秒）
    note_count: int | None = None
    bpm: float | None = None
    files: dict[str, str] | None = None   # 相对 URL
    notes: list[dict] | None = None
    created_at: float | None = None
