"""
files.py — Read-only repository file explorer endpoints.

GET /api/repositories/{repository_id}/files
  Returns the safe file tree sourced from the repository_files table.
  Files are enriched with analysis category information when available.
  Forbidden files and directories are never returned.

GET /api/repositories/{repository_id}/files/content?path=...
  Returns the content of a single repository file fetched live from GitHub.
  The path parameter is validated with validate_file_path() before any
  network request is made.

Security:
- Path traversal is rejected before any database or network access.
- Forbidden files (.env, id_rsa, *.pem, etc.) are never served.
- Binary files are detected and rejected with a clear message.
- GitHub tokens are never included in responses or error messages.
- Repository code is never executed.
- File content is returned as escaped plain text, never rendered as HTML.
"""

from fastapi import APIRouter, HTTPException, Query
from app.schemas.files import (
    FileContentResponse,
    RepositoryFileItem,
    RepositoryFileTree,
)
from app.services.github_service import (
    BINARY_EXTENSIONS,
    _CONTENT_FORBIDDEN_FILENAMES,
    get_github_file_content,
    validate_file_path,
)
from app.services.repository_service import (
    _EXTENSION_LANGUAGES,
    get_repository,
    get_supabase,
)

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/repositories", tags=["files"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_repo_or_404(repository_id: str) -> dict:
    """Retrieve repository record or raise HTTP 404."""
    try:
        repo = get_repository(repository_id)
    except Exception:
        raise HTTPException(status_code=500, detail="Database error retrieving repository.")
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found.")
    return repo


def _get_analysis_categories(repository_id: str) -> dict[str, str]:
    """
    Return a mapping of {file_path: category} for files referenced in analysis.

    Reads from the analyses table's important_files jsonb column.
    Returns an empty dict if no analysis exists or on any error.
    """
    try:
        supabase = get_supabase()
        response = (
            supabase.table("analyses")
            .select("important_files, entry_points")
            .eq("repository_id", repository_id)
            .limit(1)
            .execute()
        )
        rows = response.data or []
        if not rows:
            return {}

        row = rows[0]
        categories: dict[str, str] = {}

        # important_files: list[{file_path, category, ...}]
        important = row.get("important_files") or []
        if isinstance(important, list):
            for item in important:
                if isinstance(item, dict):
                    fp = item.get("file_path")
                    cat = item.get("category")
                    if fp and cat:
                        categories[fp] = cat

        # entry_points: list[{file_path, kind, ...}]
        entry_pts = row.get("entry_points") or []
        if isinstance(entry_pts, list):
            for ep in entry_pts:
                if isinstance(ep, dict):
                    fp = ep.get("file_path")
                    if fp and fp not in categories:
                        categories[fp] = "entry_point"

        return categories
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# GET /api/repositories/{repository_id}/files
# ---------------------------------------------------------------------------

@router.get(
    "/{repository_id}/files",
    response_model=RepositoryFileTree,
)
def list_repository_files(repository_id: str) -> RepositoryFileTree:
    """
    Return the safe file tree for a repository.

    Files are sourced from the repository_files table (metadata only —
    no content is loaded at this stage).  Forbidden files and directories
    are filtered out.  Analysis category information is merged in when
    available.

    Only files (not directories) are returned in the tree response to keep
    the payload small and immediately useful.
    """
    _get_repo_or_404(repository_id)

    # Retrieve file metadata from the repository_files table
    try:
        supabase = get_supabase()
        response = (
            supabase.table("repository_files")
            .select("file_path, file_name, extension, language, file_size, is_directory")
            .eq("repository_id", repository_id)
            .eq("is_directory", False)   # files only
            .order("file_path")
            .execute()
        )
        rows: list[dict] = response.data or []
    except Exception:
        logger.exception("Failed to query repository_files for %s", repository_id)
        raise HTTPException(
            status_code=500,
            detail="Could not load repository files.",
        )

    # Merge analysis categories
    categories = _get_analysis_categories(repository_id)

    items: list[RepositoryFileItem] = []
    for row in rows:
        file_name = row.get("file_name", "")
        file_path = row.get("file_path", "")
        extension = (row.get("extension") or "").lower()

        # Skip forbidden filenames
        if file_name.lower() in _CONTENT_FORBIDDEN_FILENAMES:
            continue
        if file_name.lower().startswith(".env"):
            continue

        # Skip binary-only extensions in the tree (they can't be previewed anyway)
        if extension in BINARY_EXTENSIONS:
            continue

        items.append(
            RepositoryFileItem(
                path=file_path,
                file_name=file_name,
                language=row.get("language"),
                extension=extension,
                file_size=row.get("file_size") or 0,
                is_directory=False,
                category=categories.get(file_path),
            )
        )

    return RepositoryFileTree(
        repository_id=repository_id,
        files=items,
        total_files=len(items),
    )


# ---------------------------------------------------------------------------
# GET /api/repositories/{repository_id}/files/content
# ---------------------------------------------------------------------------

@router.get(
    "/{repository_id}/files/content",
    response_model=FileContentResponse,
)
def get_file_content(
    repository_id: str,
    path: str = Query(..., description="Repository-relative file path"),
) -> FileContentResponse:
    """
    Return the content of a single repository file.

    The file is fetched live from GitHub using the repository's stored
    owner/name and the GitHub token from settings.

    Security:
    - path is validated before any network request.
    - Forbidden files are rejected.
    - Binary files are rejected.
    - Oversized files (> 500 KB) are rejected.
    - GitHub credentials never appear in the response.
    """
    repo = _get_repo_or_404(repository_id)

    # --- Path security ---
    ok, reason = validate_file_path(path)
    if not ok:
        raise HTTPException(status_code=400, detail=reason)

    # Check binary extension early (avoids unnecessary GitHub round-trip)
    extension = Path(path).suffix.lower()
    if extension in BINARY_EXTENSIONS:
        return FileContentResponse(
            path=path,
            file_name=Path(path).name,
            extension=extension,
            file_size=0,
            is_binary=True,
            error="Binary or unsupported file type.",
        )

    owner = repo.get("owner", "")
    name = repo.get("name", "")

    if not owner or not name:
        raise HTTPException(
            status_code=500,
            detail="Repository owner/name is not available.",
        )

    # --- Fetch from GitHub ---
    result = get_github_file_content(owner, name, path)

    # Determine language from extension
    language = _EXTENSION_LANGUAGES.get(extension)

    return FileContentResponse(
        path=path,
        file_name=Path(path).name,
        language=language,
        extension=extension,
        file_size=result["file_size"],
        content=result["content"],
        truncated=result["truncated"],
        is_binary=result["is_binary"],
        error=result["error"],
    )
