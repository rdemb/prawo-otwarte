import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    allow_eli: bool = True
    basal_enabled: bool = False
    basal_url: str = "http://127.0.0.1:8766"
    basal_timeout: float = 8.0
    basal_threshold: float = 0.80
    official_timeout: float = 12.0

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
        )
