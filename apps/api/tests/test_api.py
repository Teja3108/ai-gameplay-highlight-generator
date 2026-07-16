import asyncio
import json
from collections import namedtuple

from app import api
from app.main import app
from fastapi.testclient import TestClient


def test_health_reports_an_unconfigured_engine(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(api, "ENGINE_ROOT", None)
    monkeypatch.setattr(api, "ENGINE_PYTHON", str(tmp_path / "missing-python"))

    with TestClient(app) as client:
        response = client.get("/api/health", headers={"host": "localhost"})

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "engine_available": False,
        "engine_python_available": False,
    }


def test_upload_rejects_unsupported_files(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(api, "UPLOAD_ROOT", tmp_path / "uploads")

    with TestClient(app) as client:
        response = client.post(
            "/api/uploads",
            headers={
                "host": "localhost",
                "content-type": "video/mp4",
                "x-filename": "not-a-video.txt",
            },
            content=b"not-a-video",
        )

    assert response.status_code == 400
    assert not (tmp_path / "uploads").exists()


def test_job_requires_a_staged_upload(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(api, "UPLOAD_ROOT", tmp_path / "uploads")
    outside_file = tmp_path / "outside.mp4"
    outside_file.write_bytes(b"video")

    with TestClient(app) as client:
        response = client.post(
            "/api/jobs",
            headers={"host": "localhost"},
            json={"source_path": str(outside_file), "filename": outside_file.name},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Choose a video uploaded through this application."


def test_cancelled_queued_job_does_not_start_the_engine(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(api, "JOB_STORE_PATH", tmp_path / "jobs.json")
    job = api.JobState(
        id="queued-job",
        filename="recording.mp4",
        source_path="/tmp/recording.mp4",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        options={},
    )
    api.jobs[job.id] = job
    try:
        with TestClient(app) as client:
            response = client.post(f"/api/jobs/{job.id}/cancel", headers={"host": "localhost"})

        assert response.status_code == 200
        assert job.status == "cancelled"
    finally:
        api.jobs.pop(job.id, None)


def test_job_responses_do_not_expose_the_source_path() -> None:
    job = api.JobState(
        id="private-job",
        filename="recording.mp4",
        source_path="/private/source/recording.mp4",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        options={},
    )
    api.jobs[job.id] = job
    try:
        with TestClient(app) as client:
            response = client.get(f"/api/jobs/{job.id}", headers={"host": "localhost"})

        assert response.status_code == 200
        assert "source_path" not in response.json()
    finally:
        api.jobs.pop(job.id, None)


def test_interrupted_project_is_restored_and_marked_resumable(monkeypatch, tmp_path) -> None:
    upload_root = tmp_path / "uploads"
    upload_root.mkdir()
    source = upload_root / "recording.mp4"
    source.write_bytes(b"video")
    store_path = tmp_path / "jobs.json"
    store_path.write_text(
        json.dumps(
            [
                {
                    "id": "interrupted-job",
                    "filename": "recording.mp4",
                    "source_path": str(source),
                    "status": "processing",
                    "stage": "Finding highlights",
                    "progress": 52,
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "updated_at": "2026-01-01T00:00:00+00:00",
                    "options": {"clips": 5, "layout_mode": "auto", "review_only": False},
                    "logs": ["Finding highlights"],
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(api, "JOB_STORE_PATH", store_path)
    monkeypatch.setattr(api, "UPLOAD_ROOT", upload_root)
    api.jobs.pop("interrupted-job", None)
    try:
        api.load_jobs()
        restored = api.jobs["interrupted-job"]

        assert restored.status == "failed"
        assert restored.stage == "Interrupted"
        assert restored.progress == 52
        assert restored.source_path == str(source)
        assert "ready to resume" in (restored.error or "")
        assert restored.logs[-1] == "Service interruption detected. Project can be resumed."
    finally:
        api.jobs.pop("interrupted-job", None)


def test_malformed_project_record_does_not_hide_valid_projects(monkeypatch, tmp_path) -> None:
    store_path = tmp_path / "jobs.json"
    store_path.write_text(
        json.dumps(
            [
                {"id": "malformed"},
                {
                    "id": "valid-job",
                    "filename": "recording.mp4",
                    "source_path": "/tmp/recording.mp4",
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "updated_at": "2026-01-01T00:00:00+00:00",
                    "options": {},
                },
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(api, "JOB_STORE_PATH", store_path)
    api.jobs.pop("valid-job", None)
    try:
        api.load_jobs()
        assert api.jobs["valid-job"].filename == "recording.mp4"
    finally:
        api.jobs.pop("valid-job", None)


def test_resume_reuses_restored_project_and_keeps_its_identity(monkeypatch, tmp_path) -> None:
    upload_root = tmp_path / "uploads"
    upload_root.mkdir()
    source = upload_root / "recording.mp4"
    source.write_bytes(b"video")
    monkeypatch.setattr(api, "UPLOAD_ROOT", upload_root)
    monkeypatch.setattr(api, "JOB_STORE_PATH", tmp_path / "jobs.json")
    job = api.JobState(
        id="resume-job",
        filename="recording.mp4",
        source_path=str(source),
        status="failed",
        stage="Failed",
        progress=52,
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        options={"clips": 5, "layout_mode": "auto", "review_only": False},
    )
    api.jobs[job.id] = job

    def discard_task(coroutine):
        coroutine.close()

    monkeypatch.setattr(api.asyncio, "create_task", discard_task)
    try:
        with TestClient(app) as client:
            response = client.post(f"/api/jobs/{job.id}/resume", headers={"host": "localhost"})

        assert response.status_code == 202
        assert response.json()["id"] == job.id
        assert job.status == "queued"
        assert job.progress == 0
        assert "Project resumed." in job.logs
    finally:
        api.jobs.pop(job.id, None)


def test_resume_waits_for_a_cancelled_process_to_exit(monkeypatch, tmp_path) -> None:
    upload_root = tmp_path / "uploads"
    upload_root.mkdir()
    source = upload_root / "recording.mp4"
    source.write_bytes(b"video")
    monkeypatch.setattr(api, "UPLOAD_ROOT", upload_root)
    job = api.JobState(
        id="stopping-job",
        filename="recording.mp4",
        source_path=str(source),
        status="cancelled",
        stage="Cancelled",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        options={},
    )

    class RunningProcess:
        returncode = None

    api.jobs[job.id] = job
    api.processes[job.id] = RunningProcess()  # type: ignore[assignment]
    try:
        with TestClient(app) as client:
            response = client.post(f"/api/jobs/{job.id}/resume", headers={"host": "localhost"})

        assert response.status_code == 409
        assert "still stopping" in response.json()["detail"]
    finally:
        api.processes.pop(job.id, None)
        api.jobs.pop(job.id, None)


def test_job_serialisation_hides_transcript_and_local_clip_paths() -> None:
    job = api.JobState(
        id="private-result-job",
        filename="recording.mp4",
        source_path="/private/source/recording.mp4",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        options={},
        result={
            "transcript": {"text": "private transcript"},
            "shorts": [{"clip_url": "/private/results/clip.mp4", "start_time": 1}],
        },
    )

    payload = api.serialise(job)

    assert "transcript" not in payload["result"]
    assert "clip_url" not in payload["result"]["shorts"][0]
    assert "/private/" not in json.dumps(payload)


def test_clip_is_served_without_returning_its_path(monkeypatch, tmp_path) -> None:
    results = tmp_path / "results"
    results.mkdir()
    clip = results / "clip.mp4"
    clip.write_bytes(b"clip-data")
    monkeypatch.setattr(api, "RESULT_ROOT", results)
    job = api.JobState(
        id="clip-job",
        filename="recording.mp4",
        source_path="/private/source/recording.mp4",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        options={},
        result={"shorts": [{"clip_url": str(clip), "start_time": 1}]},
    )
    api.jobs[job.id] = job
    try:
        with TestClient(app) as client:
            response = client.get(f"/api/jobs/{job.id}/clips/0", headers={"host": "localhost"})

        assert response.status_code == 200
        assert response.content == b"clip-data"
        assert str(clip) not in response.text
    finally:
        api.jobs.pop(job.id, None)


def test_upload_rejects_a_large_file_when_disk_space_is_insufficient(monkeypatch, tmp_path) -> None:
    disk_usage = namedtuple("DiskUsage", "total used free")
    monkeypatch.setattr(api, "UPLOAD_ROOT", tmp_path / "uploads")
    monkeypatch.setattr(api.shutil, "disk_usage", lambda _: disk_usage(100, 99, 1))

    with TestClient(app) as client:
        response = client.post(
            "/api/uploads",
            headers={
                "host": "localhost",
                "content-type": "video/mp4",
                "x-filename": "recording.mp4",
                "content-length": "2",
            },
            content=b"ok",
        )

    assert response.status_code == 507
    assert response.json()["detail"] == "There is not enough free disk space to save this video."


def test_engine_marks_project_failed_when_results_storage_is_unavailable(
    monkeypatch, tmp_path
) -> None:
    unavailable_results = tmp_path / "results-file"
    unavailable_results.write_text("not a directory", encoding="utf-8")
    monkeypatch.setattr(api, "RESULT_ROOT", unavailable_results)
    monkeypatch.setattr(api, "JOB_STORE_PATH", tmp_path / "jobs.json")
    job = api.JobState(
        id="unavailable-results-job",
        filename="recording.mp4",
        source_path=str(tmp_path / "recording.mp4"),
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        options={},
    )
    api.jobs[job.id] = job
    try:
        asyncio.run(
            api.run_engine(
                job,
                api.GenerateRequest(source_path=job.source_path, filename=job.filename),
            )
        )

        assert job.status == "failed"
        assert job.error == "The local pipeline stopped unexpectedly. You can retry this project."
    finally:
        api.jobs.pop(job.id, None)


def test_review_state_is_persisted_for_a_completed_job(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(api, "JOB_STORE_PATH", tmp_path / "jobs.json")
    job = api.JobState(
        id="review-state-job",
        filename="recording.mp4",
        source_path=str(tmp_path / "recording.mp4"),
        status="completed",
        stage="Completed",
        progress=100,
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        options={"review_only": True},
        result={"highlights": [{"start_time": 1, "end_time": 8}]},
    )
    api.jobs[job.id] = job
    try:
        with TestClient(app) as client:
            response = client.put(
                f"/api/jobs/{job.id}/review",
                headers={"host": "localhost"},
                json={
                    "approved_indices": [0],
                    "rejected_indices": [],
                    "clip_edits": [{"index": 0, "start_time": 1.5, "end_time": 7.5}],
                    "active_index": 0,
                },
            )

        assert response.status_code == 200
        assert job.options["review_state"]["approved_indices"] == [0]
        assert job.options["review_state"]["clip_edits"][0]["start_time"] == 1.5
    finally:
        api.jobs.pop(job.id, None)


def test_job_source_streams_the_original_upload_without_exposing_its_path(
    monkeypatch, tmp_path
) -> None:
    upload_root = tmp_path / "uploads"
    upload_root.mkdir()
    source = upload_root / "recording.mp4"
    source.write_bytes(b"source-video")
    monkeypatch.setattr(api, "UPLOAD_ROOT", upload_root)
    job = api.JobState(
        id="source-job",
        filename="recording.mp4",
        source_path=str(source),
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        options={},
    )
    api.jobs[job.id] = job
    try:
        with TestClient(app) as client:
            response = client.get(f"/api/jobs/{job.id}/source", headers={"host": "localhost"})

        assert response.status_code == 200
        assert response.content == b"source-video"
        assert str(source) not in response.text
    finally:
        api.jobs.pop(job.id, None)


def test_review_render_rejects_invalid_selection(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(api, "JOB_STORE_PATH", tmp_path / "jobs.json")
    job = api.JobState(
        id="review-job",
        filename="recording.mp4",
        source_path=str(tmp_path / "recording.mp4"),
        status="completed",
        stage="Completed",
        progress=100,
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        options={"review_only": True},
        result={"highlights": [{"start_time": 1, "end_time": 2}]},
    )
    api.jobs[job.id] = job
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/api/jobs/{job.id}/render",
                headers={"host": "localhost"},
                json={"selected_indices": [1]},
            )

        assert response.status_code == 400
        assert response.json()["detail"] == "Choose valid, unique highlight candidates."
        assert job.status == "completed"
    finally:
        api.jobs.pop(job.id, None)


def test_review_render_rejects_edits_outside_the_detected_highlight(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(api, "JOB_STORE_PATH", tmp_path / "jobs.json")
    job = api.JobState(
        id="trimmed-review-job",
        filename="recording.mp4",
        source_path=str(tmp_path / "recording.mp4"),
        status="completed",
        stage="Completed",
        progress=100,
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        options={"review_only": True},
        result={"highlights": [{"start_time": 1, "end_time": 2}]},
    )
    api.jobs[job.id] = job
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/api/jobs/{job.id}/render",
                headers={"host": "localhost"},
                json={
                    "selected_indices": [0],
                    "clip_edits": [{"index": 0, "start_time": 0.5, "end_time": 1.5}],
                },
            )

        assert response.status_code == 400
        assert response.json()["detail"] == "Clip edits must stay within the detected highlight."
        assert job.status == "completed"
    finally:
        api.jobs.pop(job.id, None)
