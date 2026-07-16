"""HTTP surface for the local Gameplay Shorts application.

This module deliberately orchestrates the existing CLI instead of reproducing
any of its transcription, ranking, or rendering behaviour.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api")

APP_ROOT = Path(__file__).resolve().parents[3]
DATA_ROOT = Path(os.getenv("GAMEPLAY_DATA_DIR", APP_ROOT / ".data"))
UPLOAD_ROOT = DATA_ROOT / "uploads"
RESULT_ROOT = DATA_ROOT / "results"
ENGINE_ROOT = Path(
    os.getenv("GAMEPLAY_ENGINE_ROOT", "/Users/tejagoud/Developer/AI-Youtube-Shorts-Generator")
)


class GenerateRequest(BaseModel):
    source_path: str
    filename: str
    clips: Literal[3, 5, 10, 15] = 5
    game: Optional[str] = None
    layout_mode: str = "auto"
    review_only: bool = False


class JobState(BaseModel):
    id: str
    filename: str
    status: str = "queued"
    stage: str = "Preparing"
    progress: int = 0
    current_clip: Optional[str] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str
    options: dict[str, Any]
    logs: list[str] = Field(default_factory=list)
    result: Optional[dict[str, Any]] = None


jobs: dict[str, JobState] = {}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(job: JobState, message: str) -> None:
    job.logs.append(message)
    job.logs[:] = job.logs[-120:]
    job.updated_at = now()


def serialise(job: JobState) -> dict[str, Any]:
    return job.model_dump()


def stage_from_log(line: str) -> tuple[str, int] | None:
    normalized = line.lower()
    mappings = (
        (("download", "prepar"), "Preparing", 12),
        (("transcrib", "whisper"), "Transcribing", 30),
        (("highlight", "candidate", "gemini"), "Finding highlights", 52),
        (("rank", "scor"), "Ranking", 68),
        (("render", "export", "ffmpeg"), "Rendering", 82),
    )
    for terms, stage, progress in mappings:
        if any(term in normalized for term in terms):
            return stage, progress
    return None


async def run_engine(job: JobState, request: GenerateRequest) -> None:
    """Run the existing CLI asynchronously and expose its output as job state."""

    output_file = RESULT_ROOT / f"{job.id}.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    if not ENGINE_ROOT.joinpath("main.py").exists():
        job.status = "failed"
        job.error = f"Engine not found at {ENGINE_ROOT}"
        log(job, job.error)
        return

    command = [
        sys.executable,
        "main.py",
        request.source_path,
        "--mode",
        "local",
        "--clips",
        str(request.clips),
        "--layout-mode",
        request.layout_mode,
        "--output-json",
        str(output_file),
    ]
    if request.game and request.game != "auto":
        command.extend(["--game", request.game])
    if request.review_only:
        command.append("--review")

    job.status, job.stage, job.progress = "processing", "Preparing", 4
    log(job, "Starting the AI gameplay pipeline.")
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=str(ENGINE_ROOT),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        assert process.stdout is not None
        while line := await process.stdout.readline():
            message = line.decode("utf-8", errors="replace").strip()
            if message:
                log(job, message)
                detected = stage_from_log(message)
                if detected:
                    job.stage, job.progress = detected
        return_code = await process.wait()
        if return_code != 0:
            raise RuntimeError(f"Pipeline exited with code {return_code}.")
        if output_file.exists():
            job.result = json.loads(output_file.read_text(encoding="utf-8"))
        job.status, job.stage, job.progress = "completed", "Completed", 100
        log(job, "Processing completed successfully.")
    except Exception as error:  # Surface engine failures without taking down the API.
        job.status, job.stage, job.error = "failed", "Failed", str(error)
        log(job, f"Error: {error}")


@router.get("/health")
async def health() -> dict[str, Any]:
    return {"status": "ok", "engine_available": ENGINE_ROOT.joinpath("main.py").exists()}


@router.post("/uploads")
async def upload_video(request: Request) -> dict[str, str]:
    """Save a raw browser upload; no multipart parser dependency is required."""

    filename = Path(request.headers.get("x-filename", "gameplay.mp4")).name
    if not filename or filename == ".":
        raise HTTPException(status_code=400, detail="A valid X-Filename header is required.")
    content = await request.body()
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded video was empty.")
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    target = UPLOAD_ROOT / f"{uuid.uuid4().hex}_{filename}"
    target.write_bytes(content)
    return {"path": str(target), "filename": filename}


@router.post("/jobs", status_code=202)
async def create_job(payload: GenerateRequest) -> dict[str, Any]:
    source = Path(payload.source_path)
    if not source.exists():
        raise HTTPException(status_code=400, detail="The source video is no longer available.")
    job_id = uuid.uuid4().hex
    job = JobState(
        id=job_id,
        filename=payload.filename,
        created_at=now(),
        updated_at=now(),
        options=payload.model_dump(exclude={"source_path", "filename"}),
    )
    jobs[job_id] = job
    asyncio.create_task(run_engine(job, payload))
    return serialise(job)


@router.get("/jobs")
async def list_jobs() -> list[dict[str, Any]]:
    return [serialise(job) for job in sorted(jobs.values(), key=lambda item: item.created_at, reverse=True)]


@router.get("/jobs/{job_id}")
async def get_job(job_id: str) -> dict[str, Any]:
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return serialise(job)


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str) -> dict[str, Any]:
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.status == "processing":
        job.status, job.stage = "cancelled", "Cancelled"
        log(job, "Cancellation requested. The current engine process will finish its active operation.")
    return serialise(job)


@router.get("/files")
async def get_file(path: str) -> FileResponse:
    candidate = Path(path).resolve()
    allowed = [UPLOAD_ROOT.resolve(), RESULT_ROOT.resolve(), ENGINE_ROOT.resolve()]
    if not any(str(candidate).startswith(str(root)) for root in allowed) or not candidate.is_file():
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(candidate)
