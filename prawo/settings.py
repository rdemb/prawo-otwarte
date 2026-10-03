import os
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


def public_https_origin(value):
    """Deployment configuration only: one HTTPS DNS origin, without a path or secrets."""
    parsed = urlsplit(value)
    host = parsed.hostname or ""
    if (parsed.scheme != "https" or parsed.username is not None or parsed.password is not None
            or parsed.port not in (None, 443) or parsed.path not in ("", "/")
            or parsed.query or parsed.fragment or not re.fullmatch(
                r"(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}", host)
            or host.endswith((".localhost", ".local", ".internal"))
            or any(character.isspace() for character in value)):
        raise ValueError("Expected a public HTTPS DNS origin without a path, credentials or custom port.")
    return "https://" + host


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    allow_eli: bool = True
    basal_enabled: bool = False
    basal_url: str = "http://127.0.0.1:8766"
    basal_timeout: float = 8.0
    basal_threshold: float = 0.80
    official_timeout: float = 12.0
    allowed_origins: tuple[str, ...] = ()

    def __post_init__(self):
        for origin in self.allowed_origins:
            if public_https_origin(origin) != origin:
                raise ValueError("Allowed origins must use canonical HTTPS URLs without a trailing slash.")

    @classmethod
    def from_env(cls):
        return cls(
            data_dir=Path(os.getenv("PRAWO_DATA_DIR", "data")).resolve(),
            allow_eli=os.getenv("PRAWO_ALLOW_ELI", "1") == "1",
            basal_enabled=os.getenv("PRAWO_BASAL_ENABLED", "0") == "1",
            basal_url=os.getenv("PRAWO_BASAL_URL", "http://127.0.0.1:8766"),
            basal_timeout=float(os.getenv("PRAWO_BASAL_TIMEOUT", "8")),
            basal_threshold=float(os.getenv("PRAWO_BASAL_THRESHOLD", "0.80")),
            official_timeout=float(os.getenv("PRAWO_OFFICIAL_TIMEOUT", "12")),
            allowed_origins=tuple(value.strip() for value in os.getenv("PRAWO_ALLOWED_ORIGINS", "").split(",") if value.strip()),
        )
