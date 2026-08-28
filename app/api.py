"""HTTP API：上传音频 -> 异步任务 -> 下载产物。"""
from __future__ import annotations

import shutil
import threading
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from . import config
from .pipeline import run_pipeline
from .schemas import JobStatus
from .transcribe import available_engines

router = APIRouter()

JOBS: dict[str, dict] = {}
_LOCK = threading.Lock()


def _job_status(job_id: str) -> JobStatus:
    with _LOCK:
        j = dict(JOBS[job_id])
    j.pop("_input", None)
    j.pop("_engine", None)
    return JobStatus(**j)


@router.get("/api/engines")
def engines() -> dict:
    info = available_engines()
    return {
        "engines": {name: dict(v) for name, v in info.items()},
        "default": config.DEFAULT_ENGINE,
    }


@router.post("/api/jobs")
async def create_job(file: UploadFile = File(...), engine: str = Form("auto")) -> JobStatus:
    ext = Path(file.filename or "").suffix.lower()
    if ext not in config.ALLOWED_EXTENSIONS:
        raise HTTPException(
            400, f"不支持的文件类型 {ext or '(无扩展名)'}，支持：{', '.join(sorted(config.ALLOWED_EXTENSIONS))}"
        )
    data = await file.read()
    if len(data) > config.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"文件过大（上限 {config.MAX_UPLOAD_MB} MB）")

    job_id = uuid.uuid4().hex[:12]
    job_dir = config.UPLOADS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    input_path = job_dir / f"input{ext}"
    input_path.write_bytes(data)

    with _LOCK:
        JOBS[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "engine": None,
            "error": None,
            "duration": None,
            "note_count": None,
            "bpm": None,
            "files": None,
            "notes": None,
            "created_at": time.time(),
            "_input": str(input_path),
            "_engine": engine,
        }
    threading.Thread(target=_process, args=(job_id,), daemon=True).start()
    return _job_status(job_id)


def _process(job_id: str) -> None:
    with _LOCK:
        j = JOBS[job_id]
        input_path = Path(j["_input"])
        engine_name = j["_engine"]
        j["status"] = "running"

    out_dir = config.ARTIFACTS_DIR / job_id
    try:
        result = run_pipeline(input_path, out_dir, engine_name=engine_name)
        # 把原始音频复制到产物目录，供前端播放
        shutil.copy2(input_path, out_dir / input_path.name)
        files = {kind: f"/artifacts/{job_id}/{path.name}" for kind, path in result.files.items()}
        files["input"] = f"/artifacts/{job_id}/{input_path.name}"
        with _LOCK:
            JOBS[job_id].update(
                status="done",
                engine=result.engine,
                duration=round(result.duration, 3),
                note_count=len(result.notes),
                bpm=round(result.bpm, 1),
                files=files,
                notes=[n.to_dict() for n in result.notes],
            )
    except Exception as exc:  # noqa: BLE001
        with _LOCK:
            JOBS[job_id].update(status="failed", error=str(exc))


@router.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> JobStatus:
    if job_id not in JOBS:
        raise HTTPException(404, "任务不存在")
    return _job_status(job_id)


@router.get("/artifacts/{job_id}/{filename}")
def artifact(job_id: str, filename: str) -> FileResponse:
    path = config.ARTIFACTS_DIR / job_id / filename
    if not path.is_file():
        raise HTTPException(404, "文件不存在")
    return FileResponse(str(path))
