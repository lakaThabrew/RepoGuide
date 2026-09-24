import re
from app.database.supabase import get_supabase


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
