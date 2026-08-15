from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_env_file(path: str | Path | None = None) -> Path | None:
    """Load KEY=VALUE pairs from a .env file into os.environ.

    Existing environment variables are never overridden (shell/Docker wins).
    Returns the resolved path if the file was loaded, else None.
    """
    file = Path(path) if path is not None else PROJECT_ROOT / ".env"
    if not file.exists():
        return None
    for raw_line in file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
    return file
