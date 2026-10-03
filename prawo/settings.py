import os
import re
import ipaddress
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


def public_https_origin(value):
    """One configured HTTPS origin: DNS name or globally routable IP address."""
    parsed = urlsplit(value)
    host = parsed.hostname or ""
    if (parsed.scheme != "https" or parsed.username is not None or parsed.password is not None
            or parsed.port not in (None, 443) or parsed.path not in ("", "/")
            or parsed.query or parsed.fragment
            or any(character.isspace() for character in value)):
        raise ValueError("Expected a public HTTPS origin without a path, credentials or custom port.")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        if (not re.fullmatch(r"(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}", host)
                or host.endswith((".localhost", ".local", ".internal"))):
            raise ValueError("Expected a DNS name or globally routable IP address.")
    else:
        if (not address.is_global or address.is_multicast or address.is_reserved
                or getattr(address, "ipv4_mapped", None) or "%" in host):
            raise ValueError("Only globally routable IP addresses are allowed.")
        host = f"[{address.compressed}]" if address.version == 6 else str(address)
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
    generator_enabled: bool = False
    generator_url: str = "http://127.0.0.1:8767"
    generator_model: str = "bielik"
    generator_timeout: float = 90.0

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
            generator_enabled=os.getenv("PRAWO_GENERATOR_ENABLED", "0") == "1",
            generator_url=os.getenv("PRAWO_GENERATOR_URL", "http://127.0.0.1:8767"),
            generator_model=os.getenv("PRAWO_GENERATOR_MODEL", "bielik"),
            generator_timeout=float(os.getenv("PRAWO_GENERATOR_TIMEOUT", "90")),
        )
