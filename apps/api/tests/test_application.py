from app.main import app


def test_application_is_created() -> None:
    assert app is not None
