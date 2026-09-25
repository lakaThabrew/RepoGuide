import logging
import re
from app.database.supabase import get_supabase

logger = logging.getLogger(__name__)

# Language detection by extension — mirrors analysis_service.EXTENSION_LANGUAGES
# (kept here to avoid a cross-service import just for file persistence)
_EXTENSION_LANGUAGES: dict[str, str] = {
    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
    ".jsx": "JavaScript", ".tsx": "TypeScript",
    ".java": "Java", ".kt": "Kotlin", ".kts": "Kotlin",
    ".go": "Go", ".rs": "Rust", ".rb": "Ruby",
    ".php": "PHP", ".cs": "C#", ".cpp": "C++", ".c": "C",
    ".swift": "Swift", ".scala": "Scala", ".ex": "Elixir", ".exs": "Elixir",
    ".hs": "Haskell", ".clj": "Clojure", ".r": "R",
    ".sh": "Shell", ".bash": "Shell", ".zsh": "Shell",
    ".html": "HTML", ".css": "CSS", ".scss": "CSS/SCSS", ".sass": "CSS/SCSS",
    ".sql": "SQL", ".yaml": "YAML", ".yml": "YAML", ".json": "JSON",
    ".tf": "Terraform", ".hcl": "HCL",
    ".md": "Markdown", ".rst": "reStructuredText",
}

# Batch size for Supabase insert to stay within request-size limits
_INSERT_BATCH_SIZE = 100


def _parse_github_url(url: str) -> tuple[str, str]:
    """Parse owner and repo name from GitHub URL."""
    pattern = r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$"
    match = re.match(pattern, url)
    if not match:
        raise ValueError(f"Invalid GitHub URL: {url}")
    return match.group(1), match.group(2)


def create_repository(github_url: str) -> dict:
    """Create a new repository record in Supabase."""
    try:
        owner, name = _parse_github_url(github_url)
    except ValueError:
        raise

    supabase = get_supabase()
    response = (
        supabase.table("repositories")
        .insert(
            {
                "github_url": github_url,
                "owner": owner,
                "name": name,
                "status": "pending",
            }
        )
        .execute()
    )
    return response.data[0]


def get_repository(repository_id: str) -> dict | None:
    """Retrieve a repository record by ID."""
    supabase = get_supabase()
    response = (
        supabase.table("repositories")
        .select("*")
        .eq("id", repository_id)
        .single()
        .execute()
    )
    return response.data


def update_repository_status(repository_id: str, status: str) -> dict:
    """Update the status of a repository."""
    supabase = get_supabase()
    response = (
        supabase.table("repositories")
        .update({"status": status})
        .eq("id", repository_id)
        .execute()
    )
    return response.data[0]


def persist_repository_files(repository_id: str, files: list[dict]) -> int:
    """
    Persist scanned file metadata into the repository_files table.

    Idempotent: deletes all existing rows for this repository_id before
    inserting, so repeated ingestion never creates duplicates.

    Returns the number of file rows inserted.
    """
    supabase = get_supabase()

    # Delete existing rows first (makes repeated ingestion safe)
    supabase.table("repository_files").delete().eq(
        "repository_id", repository_id
    ).execute()

    if not files:
        return 0

    rows = []
    for f in files:
        ext = (f.get("extension") or "").lower()
        rows.append(
            {
                "repository_id": repository_id,
                "file_path": f["file_path"],
                "file_name": f.get("file_name", ""),
                "extension": ext,
                "language": _EXTENSION_LANGUAGES.get(ext) if not f.get("is_directory") else None,
                "file_size": f.get("file_size", 0),
                "is_directory": f.get("is_directory", False),
            }
        )

    # Insert in batches to stay within Supabase request-size limits
    inserted = 0
    for i in range(0, len(rows), _INSERT_BATCH_SIZE):
        batch = rows[i : i + _INSERT_BATCH_SIZE]
        supabase.table("repository_files").insert(batch).execute()
        inserted += len(batch)

    logger.info(
        "Persisted %d repository_files rows for repository %s",
        inserted,
        repository_id,
    )
    return inserted


def ingest_repository(repository_id: str) -> dict:
    """
    Fetch repository metadata from GitHub, clone and scan files, then persist
    them to the repository_files table.  Updates repository status accordingly.

    Returns a summary dict: {repository_id, files_scanned, status}.
    Does NOT raise — errors are captured and reflected in status.
    """
    from app.services.github_service import (
        clone_and_scan_repository,
        get_github_repo_info,
    )

    try:
        repo = get_repository(repository_id)
    except Exception as exc:
        logger.error("ingest_repository: cannot fetch repo %s: %s", repository_id, exc)
        return {"repository_id": repository_id, "status": "error",
                "error": "Could not retrieve repository record."}

    if not repo:
        return {"repository_id": repository_id, "status": "error",
                "error": "Repository not found."}

    github_url = repo.get("github_url", "")
    owner = repo.get("owner", "")
    name = repo.get("name", "")

    # Update status to 'ingesting' so callers can track progress
    try:
        update_repository_status(repository_id, "ingesting")
    except Exception as exc:
        logger.warning("Could not set status to ingesting: %s", exc)

    try:
        # Enrich repository metadata from the GitHub API
        gh_meta = get_github_repo_info(owner, name)
        if gh_meta:
            supabase = get_supabase()
            supabase.table("repositories").update(
                {
                    "description": gh_meta.get("description"),
                    "default_branch": gh_meta.get("default_branch"),
                    "language": gh_meta.get("language"),
                }
            ).eq("id", repository_id).execute()

        # Clone the repository and scan its files
        files = clone_and_scan_repository(github_url)

        # Persist to repository_files table
        count = persist_repository_files(repository_id, files)

        update_repository_status(repository_id, "scanned")

        return {
            "repository_id": repository_id,
            "status": "scanned",
            "files_scanned": count,
        }

    except Exception as exc:
        logger.exception("Ingestion failed for repository %s", repository_id)
        try:
            update_repository_status(repository_id, "error")
        except Exception:
            pass
        return {
            "repository_id": repository_id,
            "status": "error",
            "error": str(exc),
        }
