import pytest

from doctorly.core.config import Settings


def test_cors_origins_read_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "CORS_ORIGINS",
        "https://doctorly.example, https://staff.doctorly.example",
    )

    settings = Settings(_env_file=None)
    origins = [
        origin.strip()
        for origin in settings.cors_origins.split(",")
        if origin.strip()
    ]

    assert origins == [
        "https://doctorly.example",
        "https://staff.doctorly.example",
    ]
