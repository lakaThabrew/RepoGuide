import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional
import httpx
from app.config import get_settings

logger = logging.getLogger(__name__)

# Files/directories to ignore when scanning
IGNORE_DIRS = {
    ".git", "node_modules", "dist", "build", "__pycache__",
    "coverage", ".venv", "venv", ".pytest_cache", ".mypy_cache",
    ".tox", "eggs", ".eggs", "htmlcov", ".cache",
}

IGNORE_EXTENSIONS = {
    ".lock", ".log", ".bin", ".exe", ".dll", ".so", ".dylib",
    ".jpg", ".jpeg", ".png", ".gif", ".ico", ".svg", ".woff",
    ".woff2", ".ttf", ".eot", ".mp4", ".mp3", ".zip", ".tar",
    ".gz", ".rar", ".7z",
}

MAX_FILE_SIZE_BYTES = 500_000  # 500 KB per file
MAX_FILES = 300


def get_github_repo_info(owner: str, name: str) -> Optional[dict]:
    """Fetch repository metadata from GitHub API."""
    settings = get_settings()
    headers = {}
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"
    headers["Accept"] = "application/vnd.github.v3+json"

    with httpx.Client() as client:
        response = client.get(
            f"https://api.github.com/repos/{owner}/{name}",
            headers=headers,
            timeout=15.0,
        )
        if response.status_code == 200:
            return response.json()
        return None


def scan_repository_files(repo_path: str) -> list[dict]:
    """Scan a local repository and return a list of file metadata."""
    files = []
    base = Path(repo_path)

    for item in base.rglob("*"):
        # Skip ignored directories
        if any(part in IGNORE_DIRS for part in item.parts):
            continue

        if item.is_file():
            if item.suffix in IGNORE_EXTENSIONS:
                continue
            if item.stat().st_size > MAX_FILE_SIZE_BYTES:
                continue
            if len(files) >= MAX_FILES:
                break

            files.append(
                {
                    "file_path": str(item.relative_to(base)).replace("\\", "/"),
                    "file_name": item.name,
                    "extension": item.suffix,
                    "file_size": item.stat().st_size,
                    "is_directory": False,
                }
            )
        elif item.is_dir():
            if any(part in IGNORE_DIRS for part in item.parts):
                continue
            files.append(
                {
                    "file_path": str(item.relative_to(base)).replace("\\", "/"),
                    "file_name": item.name,
                    "extension": "",
                    "file_size": 0,
                    "is_directory": True,
                }
            )

    return files


# Filenames that must never be included in the scanned file list
_FORBIDDEN_FILENAMES = {
    ".env", ".env.local", ".env.production", ".env.staging",
    ".env.development", ".env.test", ".secret", "secrets.yml",
    "secrets.yaml", "id_rsa", "id_rsa.pub", "id_ed25519", "id_ed25519.pub",
    ".npmrc", ".pypirc", ".netrc", "credentials",
}


def _is_safe_path(base: Path, target: Path) -> bool:
    """Return True if target resolves inside base (prevents path traversal)."""
    try:
        target.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def clone_and_scan_repository(github_url: str) -> list[dict]:
    """
    Clone the given GitHub repository to a temporary directory, scan its files,
    and return the file list.  The clone is deleted after scanning.

    Returns an empty list on any clone failure.

    Security:
    - Forbidden filenames (.env, credentials, etc.) are excluded.
    - Path traversal is prevented via _is_safe_path.
    - The cloned code is never executed.
    """
    import git  # gitpython — listed in requirements.txt

    tmp_dir = tempfile.mkdtemp(prefix="repoguide_")
    try:
        logger.info("Cloning %s into %s", github_url, tmp_dir)
        git.Repo.clone_from(
            github_url,
            tmp_dir,
            depth=1,          # shallow clone — history not needed
            no_single_branch=False,
        )
        files = scan_repository_files(tmp_dir)
        # Post-filter: remove forbidden filenames regardless of path
        safe_files = []
        base = Path(tmp_dir)
        for f in files:
            name_lower = f["file_name"].lower()
            if name_lower in _FORBIDDEN_FILENAMES:
                logger.warning("Excluding forbidden file from scan: %s", f["file_path"])
                continue
            # Prevent path traversal in stored paths
            candidate = base / f["file_path"]
            if not _is_safe_path(base, candidate):
                logger.warning("Path traversal attempt excluded: %s", f["file_path"])
                continue
            safe_files.append(f)
        return safe_files
    except Exception as exc:
        logger.error("Failed to clone %s: %s", github_url, exc)
        return []
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
