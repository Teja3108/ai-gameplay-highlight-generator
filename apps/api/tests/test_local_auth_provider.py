from app.domain.entities.user import User
from app.infrastructure.auth.local_auth_provider import LocalAuthProvider


def test_local_auth_provider_returns_default_local_user():
    user = LocalAuthProvider().get_current_user()

    assert user == User(identifier="local-user", username="local")


def test_local_auth_provider_can_be_configured_with_a_local_user():
    configured_user = User(identifier="developer", username="Developer")

    assert LocalAuthProvider(configured_user).get_current_user() == configured_user
