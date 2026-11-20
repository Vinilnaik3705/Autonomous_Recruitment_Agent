"""Phase 1 configuration smoke tests; no real secrets or services required."""

from backend.config import Settings


def test_settings_parses_origins():
    settings = Settings(
        database_url="postgresql://test:test@localhost/test",
        jwt_secret="test-only-secret",
        cors_origins="http://localhost:5173, https://example.com",
        _env_file=None,
    )
    assert settings.allowed_origins == [
        "http://localhost:5173",
        "https://example.com",
    ]


def test_provider_default():
    settings = Settings(
        database_url="postgresql://test:test@localhost/test",
        jwt_secret="test-only-secret",
        _env_file=None,
    )
    assert settings.llm_provider == "gemini"
