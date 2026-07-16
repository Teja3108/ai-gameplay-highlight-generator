"""HTTP surface for the local Gameplay Shorts application.

This module deliberately orchestrates the existing CLI instead of reproducing
any of its transcription, ranking, or rendering behaviour.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api")

APP_ROOT = Path(__file__).resolve().parents[3]
DATA_ROOT = Path(os.getenv("GAMEPLAY_DATA_DIR", APP_ROOT / ".data"))
UPLOAD_ROOT = DATA_ROOT / "uploads"
RESULT_ROOT = DATA_ROOT / "results"
JOB_STORE_PATH = DATA_ROOT / "jobs.json"
_engine_root = os.getenv("GAMEPLAY_ENGINE_ROOT")
ENGINE_ROOT = Path(_engine_root).expanduser().resolve() if _engine_root else None
ENGINE_OUTPUT_ROOT = (
    Path(
        os.getenv(
            "GAMEPLAY_ENGINE_OUTPUT_DIR",
            ENGINE_ROOT / "output" if ENGINE_ROOT else RESULT_ROOT,
        )
    )
    .expanduser()
    .resolve()
)
ENGINE_PYTHON = os.getenv("GAMEPLAY_ENGINE_PYTHON", sys.executable)
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024 * 1024)))
MAX_CONCURRENT_JOBS = int(os.getenv("MAX_CONCURRENT_JOBS", "1"))
SUPPORTED_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm"}


class GenerateRequest(BaseModel):
    source_path: str = Field(min_length=1, max_length=2048)
    filename: str = Field(min_length=1, max_length=255)
    clips: Literal[3, 5, 10, 15] = 5
    game: Literal["auto", "tlou", "gta6", "cyberpunk"] | None = None
    layout_mode: Literal["auto", "single", "dialogue", "split"] = "auto"
    review_only: bool = False


class JobState(BaseModel):
    id: str
    filename: str
    status: str = "queued"
    stage: str = "Preparing"
    progress: int = 0
    current_clip: str | None = None
    error: str | None = None
    created_at: str
    updated_at: str
    options: dict[str, Any]
    source_path: str
    logs: list[str] = Field(default_factory=list)
    result: dict[str, Any] | None = None


jobs: dict[str, JobState] = {}
processes: dict[str, asyncio.subprocess.Process] = {}


class ClipEdit(BaseModel):
    index: int = Field(ge=0)
    start_time: float = Field(ge=0)
    end_time: float = Field(gt=0)


class RenderRequest(BaseModel):
    selected_indices: list[int] = Field(min_length=1, max_length=15)
    clip_edits: list[ClipEdit] = Field(default_factory=list, max_length=15)


class ReviewState(BaseModel):
    approved_indices: list[int] = Field(default_factory=list, max_length=15)
    rejected_indices: list[int] = Field(default_factory=list, max_length=15)
    clip_edits: list[ClipEdit] = Field(default_factory=list, max_length=15)
    active_index: int = Field(default=0, ge=0)


REVIEW_RENDER_SCRIPT = """
import json
import sys

from shorts_generator.local.clipper import crop_highlights_local

source_path, payload_path, output_dir, layout_mode, result_path = sys.argv[1:]
with open(payload_path, encoding="utf-8") as source:
    payload = json.load(source)
shorts = crop_highlights_local(
    source_path,
    payload["highlights"],
    out_dir=output_dir,
    transcript=payload.get("transcript"),
    layout_mode=layout_mode,
)
with open(result_path, "w", encoding="utf-8") as destination:
    json.dump(shorts, destination)
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_jobs() -> None:
    """Persist local project state atomically so completed work can be resumed."""

    JOB_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = JOB_STORE_PATH.with_suffix(".tmp")
    temporary_path.write_text(
        json.dumps([job.model_dump() for job in jobs.values()], indent=2), encoding="utf-8"
    )
    temporary_path.replace(JOB_STORE_PATH)


def load_jobs() -> None:
    """Restore saved projects and mark interrupted work as recoverable."""

    if not JOB_STORE_PATH.is_file():
        return
    try:
        saved_jobs = json.loads(JOB_STORE_PATH.read_text(encoding="utf-8"))
        for saved_job in saved_jobs:
            job = JobState.model_validate(saved_job)
            if job.status in {"queued", "processing"}:
                job.status, job.stage = "failed", "Interrupted"
                job.error = (
                    "The local service stopped before this project finished. "
                    "Resume it to try again."
                )
                job.updated_at = now()
            jobs[job.id] = job
        save_jobs()
    except (json.JSONDecodeError, OSError, ValueError):
        # A corrupt local history must not prevent the service from starting.
        jobs.clear()


def log(job: JobState, message: str) -> None:
    job.logs.append(message)
    job.logs[:] = job.logs[-120:]
    job.updated_at = now()
    save_jobs()


def serialise(job: JobState) -> dict[str, Any]:
    return job.model_dump(exclude={"source_path"})


def is_within(path: Path, root: Path) -> bool:
    """Return whether a resolved path belongs to a resolved root directory."""

    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def allowed_source(path: Path) -> bool:
    return is_within(path, UPLOAD_ROOT.resolve()) and path.suffix.lower() in SUPPORTED_EXTENSIONS


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

    if job.status == "cancelled":
        return
    output_file = RESULT_ROOT / f"{job.id}.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    if ENGINE_ROOT is None or not ENGINE_ROOT.joinpath("main.py").is_file():
        job.status = "failed"
        job.error = "The gameplay engine is not configured or its main.py file is unavailable."
        log(job, job.error)
        return

    command = [
        ENGINE_PYTHON,
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
        processes[job.id] = process
        assert process.stdout is not None
        while line := await process.stdout.readline():
            message = line.decode("utf-8", errors="replace").strip()
            if message:
                log(job, message)
                detected = stage_from_log(message)
                if detected:
                    job.stage, job.progress = detected
        return_code = await process.wait()
        if job.status == "cancelled":
            log(job, "Processing cancelled.")
            return
        if return_code != 0:
            raise RuntimeError(f"Pipeline exited with code {return_code}.")
        if not output_file.is_file():
            raise RuntimeError("Pipeline completed without producing its result file.")
        result = json.loads(output_file.read_text(encoding="utf-8"))
        if not isinstance(result, dict) or not isinstance(result.get("highlights"), list):
            raise RuntimeError("Pipeline produced an invalid result file.")
        job.result = result
        job.status, job.stage, job.progress = "completed", "Completed", 100
        log(job, "Processing completed successfully.")
    except Exception as error:  # Surface engine failures without taking down the API.
        if job.status == "cancelled":
            log(job, "Processing cancelled.")
            return
        job.status, job.stage, job.error = "failed", "Failed", str(error)
        log(job, f"Error: {error}")
    finally:
        processes.pop(job.id, None)


async def run_review_render(
    job: JobState, selected_indices: list[int], clip_edits: list[ClipEdit]
) -> None:
    """Render previously reviewed candidates using the engine's existing clip renderer."""

    if job.status == "cancelled":
        return
    if ENGINE_ROOT is None or job.result is None:
        job.status, job.stage = "failed", "Failed"
        job.error = "The local renderer is unavailable."
        log(job, job.error)
        return

    highlights = job.result.get("highlights", [])
    edits_by_index = {edit.index: edit for edit in clip_edits}
    selected_highlights = []
    for index in selected_indices:
        highlight = dict(highlights[index])
        if edit := edits_by_index.get(index):
            highlight["start_time"] = edit.start_time
            highlight["end_time"] = edit.end_time
        selected_highlights.append(highlight)
    render_root = RESULT_ROOT / job.id
    render_root.mkdir(parents=True, exist_ok=True)
    payload_path = render_root / "selection.json"
    rendered_path = render_root / "rendered.json"
    payload_path.write_text(
        json.dumps(
            {
                "highlights": selected_highlights,
                "transcript": job.result.get("transcript", {}),
            }
        ),
        encoding="utf-8",
    )
    command = [
        ENGINE_PYTHON,
        "-c",
        REVIEW_RENDER_SCRIPT,
        job.source_path,
        str(payload_path),
        str(render_root),
        str(job.options.get("layout_mode", "auto")),
        str(rendered_path),
    ]
    job.status, job.stage, job.progress, job.error = "processing", "Rendering", 82, None
    log(job, f"Rendering {len(selected_highlights)} selected highlight(s).")
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=str(ENGINE_ROOT),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        processes[job.id] = process
        assert process.stdout is not None
        while line := await process.stdout.readline():
            message = line.decode("utf-8", errors="replace").strip()
            if message:
                log(job, message)
        return_code = await process.wait()
        if job.status == "cancelled":
            log(job, "Rendering cancelled.")
            return
        if return_code != 0 or not rendered_path.is_file():
            raise RuntimeError("The renderer did not produce any clips.")
        job.result["shorts"] = json.loads(rendered_path.read_text(encoding="utf-8"))
        job.status, job.stage, job.progress = "completed", "Completed", 100
        log(job, "Selected clips rendered successfully.")
    except Exception as error:
        if job.status == "cancelled":
            log(job, "Rendering cancelled.")
            return
        job.status, job.stage, job.error = "failed", "Failed", str(error)
        log(job, f"Error: {error}")
    finally:
        processes.pop(job.id, None)


@router.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "engine_available": ENGINE_ROOT is not None and ENGINE_ROOT.joinpath("main.py").is_file(),
        "engine_python_available": Path(ENGINE_PYTHON).exists(),
    }


@router.post("/uploads")
async def upload_video(request: Request) -> dict[str, str]:
    """Stream a bounded raw browser upload into the local upload directory."""

    filename = Path(request.headers.get("x-filename", "gameplay.mp4")).name
    if not filename or filename == "." or Path(filename).suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="A valid X-Filename header is required.")
    content_type = request.headers.get("content-type", "")
    if not content_type.startswith("video/"):
        raise HTTPException(status_code=415, detail="Upload a supported video file.")
    declared_length = request.headers.get("content-length")
    if declared_length:
        try:
            if int(declared_length) > MAX_UPLOAD_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail="The uploaded video exceeds the configured size limit.",
                )
        except ValueError as error:
            raise HTTPException(
                status_code=400, detail="Content-Length must be a valid number."
            ) from error
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    target = UPLOAD_ROOT / f"{uuid.uuid4().hex}_{filename}"
    bytes_written = 0
    try:
        with target.open("xb") as upload:
            async for chunk in request.stream():
                bytes_written += len(chunk)
                if bytes_written > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail="The uploaded video exceeds the configured size limit.",
                    )
                upload.write(chunk)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    if not bytes_written:
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="The uploaded video was empty.")
    return {"path": str(target), "filename": filename}


@router.post("/jobs", status_code=202)
async def create_job(payload: GenerateRequest) -> dict[str, Any]:
    source = Path(payload.source_path).resolve()
    if not source.is_file() or not allowed_source(source):
        raise HTTPException(
            status_code=400, detail="Choose a video uploaded through this application."
        )
    active_jobs = sum(job.status in {"queued", "processing"} for job in jobs.values())
    if active_jobs >= MAX_CONCURRENT_JOBS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Another video is already being processed. "
                "Wait for it to finish before starting a new one."
            ),
        )
    job_id = uuid.uuid4().hex
    job = JobState(
        id=job_id,
        filename=payload.filename,
        source_path=str(source),
        created_at=now(),
        updated_at=now(),
        options=payload.model_dump(exclude={"source_path", "filename"}),
    )
    jobs[job_id] = job
    save_jobs()
    asyncio.create_task(run_engine(job, payload))
    return serialise(job)


@router.get("/jobs")
async def list_jobs() -> list[dict[str, Any]]:
    return [
        serialise(job)
        for job in sorted(jobs.values(), key=lambda item: item.created_at, reverse=True)
    ]


@router.get("/jobs/{job_id}")
async def get_job(job_id: str) -> dict[str, Any]:
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return serialise(job)


@router.get("/jobs/{job_id}/source")
async def get_job_source(job_id: str) -> FileResponse:
    """Stream a job's original upload without exposing its local filesystem path."""

    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    source = Path(job.source_path).resolve()
    if not source.is_file() or not allowed_source(source):
        raise HTTPException(status_code=404, detail="The original upload is no longer available.")
    return FileResponse(source)


@router.put("/jobs/{job_id}/review")
async def save_review_state(job_id: str, payload: ReviewState) -> dict[str, Any]:
    """Persist non-destructive review decisions alongside the existing job state."""

    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    highlights = (job.result or {}).get("highlights", [])
    all_indices = payload.approved_indices + payload.rejected_indices
    if (
        len(set(all_indices)) != len(all_indices)
        or any(index < 0 or index >= len(highlights) for index in all_indices)
        or payload.active_index >= max(len(highlights), 1)
    ):
        raise HTTPException(
            status_code=400, detail="Review state contains invalid highlight choices."
        )
    if len({edit.index for edit in payload.clip_edits}) != len(payload.clip_edits):
        raise HTTPException(status_code=400, detail="Review state contains duplicate clip edits.")
    for edit in payload.clip_edits:
        if edit.index not in payload.approved_indices or edit.index >= len(highlights):
            raise HTTPException(
                status_code=400, detail="Clip edits must belong to approved highlights."
            )
        original = highlights[edit.index]
        if (
            edit.end_time <= edit.start_time
            or edit.start_time < float(original["start_time"])
            or edit.end_time > float(original["end_time"])
        ):
            raise HTTPException(
                status_code=400, detail="Clip edits must stay within the detected highlight."
            )
    job.options["review_state"] = payload.model_dump()
    job.updated_at = now()
    save_jobs()
    return serialise(job)


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str) -> dict[str, Any]:
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.status in {"queued", "processing"}:
        job.status, job.stage = "cancelled", "Cancelled"
        process = processes.get(job_id)
        if process and process.returncode is None:
            process.terminate()
        log(job, "Cancellation requested. Stopping the current engine process.")
    return serialise(job)


@router.post("/jobs/{job_id}/resume", status_code=202)
async def resume_job(job_id: str) -> dict[str, Any]:
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.status not in {"failed", "cancelled"}:
        raise HTTPException(
            status_code=409, detail="Only failed or cancelled projects can be resumed."
        )
    source = Path(job.source_path).resolve()
    if not source.is_file() or not allowed_source(source):
        raise HTTPException(
            status_code=400, detail="The original uploaded video is no longer available."
        )
    active_jobs = sum(candidate.status in {"queued", "processing"} for candidate in jobs.values())
    if active_jobs >= MAX_CONCURRENT_JOBS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Another video is already being processed. Wait for it to finish before resuming."
            ),
        )
    job.status, job.stage, job.progress, job.error = "queued", "Preparing", 0, None
    log(job, "Project resumed.")
    request = GenerateRequest(
        source_path=job.source_path,
        filename=job.filename,
        **job.options,
    )
    asyncio.create_task(run_engine(job, request))
    return serialise(job)


@router.post("/jobs/{job_id}/render", status_code=202)
async def render_selected_clips(job_id: str, payload: RenderRequest) -> dict[str, Any]:
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.status != "completed" or not job.options.get("review_only") or not job.result:
        raise HTTPException(
            status_code=409, detail="This project is not ready for review rendering."
        )
    selected_indices = sorted(set(payload.selected_indices))
    highlights = job.result.get("highlights", [])
    if len(selected_indices) != len(payload.selected_indices) or any(
        index < 0 or index >= len(highlights) for index in selected_indices
    ):
        raise HTTPException(status_code=400, detail="Choose valid, unique highlight candidates.")
    if len({edit.index for edit in payload.clip_edits}) != len(payload.clip_edits):
        raise HTTPException(status_code=400, detail="Choose at most one edit for each highlight.")
    for edit in payload.clip_edits:
        if edit.index not in selected_indices or edit.index >= len(highlights):
            raise HTTPException(
                status_code=400, detail="Clip edits must belong to selected highlights."
            )
        original = highlights[edit.index]
        if (
            edit.end_time <= edit.start_time
            or edit.start_time < float(original["start_time"])
            or edit.end_time > float(original["end_time"])
        ):
            raise HTTPException(
                status_code=400, detail="Clip edits must stay within the detected highlight."
            )
    active_jobs = sum(candidate.status in {"queued", "processing"} for candidate in jobs.values())
    if active_jobs >= MAX_CONCURRENT_JOBS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Another video is already being processed. Wait for it to finish before rendering."
            ),
        )
    job.status, job.stage, job.progress, job.error = "queued", "Preparing", 0, None
    log(job, "Rendering selected highlights.")
    asyncio.create_task(run_review_render(job, selected_indices, payload.clip_edits))
    return serialise(job)


@router.get("/files")
async def get_file(path: str) -> FileResponse:
    candidate = Path(path).resolve()
    allowed = [
        UPLOAD_ROOT.resolve(),
        RESULT_ROOT.resolve(),
        ENGINE_OUTPUT_ROOT.resolve(),
    ]
    if not any(is_within(candidate, root) for root in allowed) or not candidate.is_file():
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(candidate)
