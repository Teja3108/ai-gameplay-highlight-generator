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
