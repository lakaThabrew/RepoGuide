import base64
import logging
import os
import re
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

# Additional binary/media extensions rejected at the content-fetch level.
# These supplement IGNORE_EXTENSIONS (which governs the clone scanner).
BINARY_EXTENSIONS = IGNORE_EXTENSIONS | {
    ".webp", ".pdf", ".wasm", ".mov", ".mp4", ".mp3", ".ico",
    ".bmp", ".tiff", ".tif", ".psd", ".ai", ".sketch",
    ".dmg", ".iso", ".deb", ".rpm", ".apk", ".ipa",
    ".class", ".pyc", ".pyo", ".o", ".a", ".lib",
    ".pem", ".der", ".crt", ".p12", ".pfx",
}

MAX_FILE_SIZE_BYTES = 500_000  # 500 KB per file
MAX_FILES = 300

# ---------------------------------------------------------------------------
# Safe-path validation for the file-content endpoint
# ---------------------------------------------------------------------------

# Forbidden file names — must never be served via the content endpoint.
# This is the authoritative set; the clone-scan filter (_FORBIDDEN_FILENAMES)
# mirrors it but is applied at ingestion time.
_CONTENT_FORBIDDEN_FILENAMES: frozenset[str] = frozenset({
    ".env", ".env.local", ".env.production", ".env.staging",
    ".env.development", ".env.test", ".secret", "secrets.yml",
    "secrets.yaml", "id_rsa", "id_rsa.pub", "id_ed25519", "id_ed25519.pub",
    ".npmrc", ".pypirc", ".netrc", "credentials",
})

# Forbidden file extensions — e.g. private keys, certificates, pem files.
_CONTENT_FORBIDDEN_EXTENSIONS: frozenset[str] = frozenset({
    ".pem", ".key", ".p12", ".pfx", ".crt", ".cer", ".der",
})

# Pre-compiled patterns that must never appear in a path argument.
_TRAVERSAL_PATTERNS = re.compile(
    r"(\.\.[/\\])"          # ../  or ..\
    r"|(^/)"                # absolute Unix path
    r"|(^[A-Za-z]:[/\\])"  # absolute Windows path (C:\ or C:/)
    r"|\x00"                # null byte
    r"|%2e%2e"              # URL-encoded ..  (case-insensitive checked separately)
    r"|%252e"               # double-encoded %
    r"|%00",                # URL-encoded null byte
    re.IGNORECASE,
)


def validate_file_path(path: str) -> tuple[bool, str]:
    """
    Validate a repository-relative file path submitted by the user.

    Returns (True, "") when the path is safe.
    Returns (False, reason) when the path must be rejected.

    This is the single authoritative path-security function.  All file-content
    endpoints MUST call it before acting on a user-supplied path.
    """
    if not path or not path.strip():
        return False, "File path must not be empty."

    path = path.strip()

    # Reject traversal patterns
    if _TRAVERSAL_PATTERNS.search(path):
        return False, "Invalid file path."

    # Also check after URL-decoding one level (catch %2F, %2E%2E etc.)
    try:
        from urllib.parse import unquote
        decoded = unquote(path)
        if _TRAVERSAL_PATTERNS.search(decoded):
            return False, "Invalid file path."
    except Exception:
        pass

    # Reject forbidden filenames (basename check)
    name = Path(path).name.lower()
    if name in _CONTENT_FORBIDDEN_FILENAMES:
        return False, "This file cannot be previewed."

    # Reject forbidden extensions
    suffix = Path(path).suffix.lower()
    if suffix in _CONTENT_FORBIDDEN_EXTENSIONS:
        return False, "This file cannot be previewed."

    # Reject .env-like names (e.g. .env.custom)
    if name.startswith(".env"):
        return False, "This file cannot be previewed."

    return True, ""


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


# ---------------------------------------------------------------------------
# GitHub file-content retrieval (used by the file explorer endpoint)
# ---------------------------------------------------------------------------

def get_github_file_content(owner: str, repo: str, path: str) -> dict:
    """
    Retrieve the content of a single file from GitHub's contents API.

    Returns a dict with the following keys:

      content     str | None   — decoded UTF-8 text, or None for binary/error
      file_size   int          — file size in bytes
      is_binary   bool         — True when the file is binary or cannot be decoded
      truncated   bool         — always False (we refuse oversized, not truncate)
      error       str | None   — safe human-readable error message (no tokens/traces)

    Security:
    - The caller MUST have validated `path` with validate_file_path() first.
    - This function never leaks the GitHub token in return values or exceptions.
    - It never executes any content from the repository.
    """
    settings = get_settings()
    headers: dict[str, str] = {"Accept": "application/vnd.github.v3+json"}
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"

    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"

    try:
        with httpx.Client() as client:
            response = client.get(url, headers=headers, timeout=15.0)
    except httpx.TimeoutException:
        logger.warning("GitHub API timeout for %s/%s path=%s", owner, repo, path)
        return {"content": None, "file_size": 0, "is_binary": False,
                "truncated": False, "error": "Request timed out. Please try again."}
    except httpx.RequestError as exc:
        logger.warning("GitHub API request error for %s/%s: %s", owner, repo, type(exc).__name__)
        return {"content": None, "file_size": 0, "is_binary": False,
                "truncated": False, "error": "Could not reach GitHub. Please try again."}

    if response.status_code == 404:
        return {"content": None, "file_size": 0, "is_binary": False,
                "truncated": False, "error": "File not found in repository."}

    if response.status_code == 403:
        return {"content": None, "file_size": 0, "is_binary": False,
                "truncated": False, "error": "Access denied. The repository may be private or rate-limited."}

    if response.status_code != 200:
        logger.warning(
            "GitHub API returned %d for %s/%s path=%s",
            response.status_code, owner, repo, path,
        )
        return {"content": None, "file_size": 0, "is_binary": False,
                "truncated": False, "error": "Could not retrieve file from GitHub."}

    try:
        data = response.json()
    except Exception:
        logger.warning("GitHub API returned non-JSON for %s/%s path=%s", owner, repo, path)
        return {"content": None, "file_size": 0, "is_binary": False,
                "truncated": False, "error": "Unexpected response from GitHub."}

    # GitHub returns a list for directories
    if isinstance(data, list):
        return {"content": None, "file_size": 0, "is_binary": False,
                "truncated": False, "error": "Path refers to a directory, not a file."}

    file_size: int = data.get("size", 0)

    # Reject oversized files
    if file_size > MAX_FILE_SIZE_BYTES:
        return {"content": None, "file_size": file_size, "is_binary": False,
                "truncated": False, "error": "File too large to preview."}

    # GitHub encodes file contents as base64
    encoding = data.get("encoding", "")
    raw_content = data.get("content", "")

    if encoding != "base64" or not raw_content:
        # Binary files or submodules may have no content
        return {"content": None, "file_size": file_size, "is_binary": True,
                "truncated": False, "error": "Binary or unsupported file type."}

    # Decode base64 safely
    try:
        # GitHub's base64 includes newlines — strip them before decoding
        decoded_bytes = base64.b64decode(raw_content.replace("\n", ""))
    except Exception:
        logger.warning("Invalid base64 from GitHub for %s/%s path=%s", owner, repo, path)
        return {"content": None, "file_size": file_size, "is_binary": True,
                "truncated": False, "error": "Binary or unsupported file type."}

    # Detect binary by checking for null bytes in the first 8 KB
    probe = decoded_bytes[:8192]
    if b"\x00" in probe:
        return {"content": None, "file_size": file_size, "is_binary": True,
                "truncated": False, "error": "Binary or unsupported file type."}

    # Decode as UTF-8 text
    try:
        text = decoded_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return {"content": None, "file_size": file_size, "is_binary": True,
                "truncated": False, "error": "Binary or unsupported file type."}

    return {"content": text, "file_size": file_size, "is_binary": False,
            "truncated": False, "error": None}
