from app.infrastructure.persistence.models.clip import Clip
from app.infrastructure.persistence.models.job import Job
from app.infrastructure.persistence.models.settings import Settings
from app.infrastructure.persistence.models.video import Video
from app.infrastructure.persistence.repositories.clip_repository import ClipRepository
from app.infrastructure.persistence.repositories.job_repository import JobRepository
from app.infrastructure.persistence.repositories.settings_repository import (
    SettingsRepository,
)
from app.infrastructure.persistence.repositories.video_repository import VideoRepository


def test_video_repository_persists_and_lists_videos(session_factory):
    repository = VideoRepository(session_factory)
    video = repository.add(
        Video(
            filename="match.mp4",
            original_path="/videos/match.mp4",
            duration=120.5,
            resolution="1920x1080",
            fps=60.0,
            size_bytes=1_000_000,
        )
    )

    assert video.id is not None
    assert repository.get(video.id).filename == "match.mp4"
    assert [stored.id for stored in repository.list()] == [video.id]


def test_clip_repository_persists_clips_for_a_video(session_factory):
    videos = VideoRepository(session_factory)
    clips = ClipRepository(session_factory)
    video = videos.add(
        Video(
            filename="match.mp4",
            original_path="/videos/match.mp4",
            duration=120.5,
            resolution="1920x1080",
            fps=60.0,
            size_bytes=1_000_000,
        )
    )
    clip = clips.add(Clip(video_id=video.id, start_time=4.0, end_time=14.0, viral_score=0.82))

    assert [stored.id for stored in clips.list_for_video(video.id)] == [clip.id]


def test_job_repository_persists_jobs(session_factory):
    repository = JobRepository(session_factory)
    job = repository.add(Job())

    stored = repository.get(job.id)

    assert stored is not None
    assert stored.status == "pending"
    assert stored.progress == 0.0


def test_settings_repository_saves_and_updates_settings(session_factory):
    repository = SettingsRepository(session_factory)
    settings = repository.save(
        Settings(
            output_directory="/output",
            temp_directory="/tmp/highlights",
            preferred_gpu="local-gpu",
            subtitle_enabled=True,
            smart_crop_enabled=True,
        )
    )
    settings.subtitle_enabled = False

    updated = repository.save(settings)

    assert updated.id == settings.id
    assert repository.get(updated.id).subtitle_enabled is False
