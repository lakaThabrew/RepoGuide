import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional
import httpx
from app.config import get_settings

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
