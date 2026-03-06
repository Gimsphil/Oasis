from __future__ import annotations

import os
from pathlib import Path


def _repo_root() -> Path:
    # .../SANCHUL_Sheet_1/utils/path_config.py -> .../SANCHUL_Sheet_1
    return Path(__file__).resolve().parent.parent


REPO_ROOT = _repo_root()
OASIS_ROOT = Path(os.getenv("OASIS_ROOT", REPO_ROOT.parent))
SANCHUL_ROOT = Path(os.getenv("OASIS_SANCHUL_ROOT", REPO_ROOT))

CONFIG_DIR = Path(os.getenv("OASIS_CONFIG_DIR", OASIS_ROOT / "config"))
DB_DIR = Path(os.getenv("OASIS_DB_DIR", OASIS_ROOT / "db1"))
LOG_DIR = Path(os.getenv("OASIS_LOG_DIR", OASIS_ROOT / "logs"))


def resolve_path(*parts: str) -> str:
    """Return an absolute path under SANCHUL_ROOT."""
    return str(SANCHUL_ROOT.joinpath(*parts))

