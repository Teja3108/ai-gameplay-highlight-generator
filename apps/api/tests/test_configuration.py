import pytest
from app.domain.entities.runtime import GpuPreference, LogLevel
from app.infrastructure.config.environment_config_provider import EnvironmentConfigProvider


def test_config_provider_loads_typed_values_from_dotenv_file(tmp_path):
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "DATABASE_URL=sqlite:///./configured.db\n"
        "STORAGE_ROOT=./storage\n"
        "TEMP_DIRECTORY=./temp\n"
        "LOG_LEVEL=debug\n"
        "GPU_PREFERENCE=mps\n"
        "MODEL_CACHE_PATH=./models\n"
        "OUTPUT_DIRECTORY=./output\n"
    )

    config = EnvironmentConfigProvider(environment={}, dotenv_path=dotenv_path).get_config()

    assert config.database_url == "sqlite:///./configured.db"
    assert config.storage_root.as_posix() == "storage"
    assert config.log_level is LogLevel.DEBUG
    assert config.gpu_preference is GpuPreference.MPS


def test_environment_values_override_dotenv_values(tmp_path):
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text("LOG_LEVEL=ERROR\nGPU_PREFERENCE=cpu\n")

    config = EnvironmentConfigProvider(
        environment={"LOG_LEVEL": "warning", "GPU_PREFERENCE": "cuda"}, dotenv_path=dotenv_path
    ).get_config()

    assert config.log_level is LogLevel.WARNING
    assert config.gpu_preference is GpuPreference.CUDA


def test_config_provider_rejects_invalid_values(tmp_path):
    with pytest.raises(ValueError, match="LOG_LEVEL"):
        EnvironmentConfigProvider(
            environment={"LOG_LEVEL": "verbose"}, dotenv_path=tmp_path / "missing.env"
        )

    with pytest.raises(ValueError, match="DATABASE_URL"):
        EnvironmentConfigProvider(
            environment={"DATABASE_URL": "not-a-url"}, dotenv_path=tmp_path / "missing.env"
        )
