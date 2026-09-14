"""
Version and Build Information Management for Prisma SASE 5G Manager.
Automatically computes dynamic version numbers based on Git history and build metadata.
"""

import os
import subprocess
from functools import lru_cache
from typing import Dict, Any

DEFAULT_BASE_VERSION = "2.3.4"
FALLBACK_BUILD_NUMBER = 43
FALLBACK_COMMIT = "90c6afc"
RELEASE_DATE = "2026-09-14"


def _get_git_commit_count(repo_dir: str) -> int:
    """Retrieve total git commit count if git is installed and repository exists."""
    try:
        res = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=2,
            check=True
        )
        return int(res.stdout.strip())
    except Exception:
        return FALLBACK_BUILD_NUMBER


def _get_git_commit_hash(repo_dir: str) -> str:
    """Retrieve short commit hash if git is installed."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=2,
            check=True
        )
        return res.stdout.strip()
    except Exception:
        return FALLBACK_COMMIT


@lru_cache(maxsize=1)
def get_version_info() -> Dict[str, Any]:
    """
    Get application version information.
    Prioritizes APP_VERSION environment variable if provided,
    otherwise resolves dynamically from git metadata.
    """
    repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Check environment override
    env_version = os.environ.get("APP_VERSION", "").strip()
    env_commit = os.environ.get("GIT_COMMIT", "").strip()
    
    # Read version file if present
    version_file_path = os.path.join(repo_dir, "VERSION")
    file_version = ""
    if os.path.isfile(version_file_path):
        try:
            with open(version_file_path, "r", encoding="utf-8") as f:
                file_version = f.read().strip()
        except Exception:
            pass

    commit_count = _get_git_commit_count(repo_dir)
    commit_sha = env_commit or _get_git_commit_hash(repo_dir)

    if env_version:
        version_str = env_version
    elif file_version:
        version_str = file_version
    else:
        version_str = f"{DEFAULT_BASE_VERSION}.{commit_count}"

    return {
        "version": version_str,
        "commit": commit_sha,
        "display": f"{version_str}",
        "full": f"{version_str} ({commit_sha})",
        "base_version": DEFAULT_BASE_VERSION,
        "build": commit_count,
        "release_date": RELEASE_DATE
    }


__version__ = get_version_info()["version"]
