from fastapi import APIRouter, HTTPException
from app.schemas.repository import RepositoryCreate, RepositoryResponse
from app.services import repository_service

router = APIRouter(prefix="/api/repositories", tags=["repositories"])


@router.post("", response_model=RepositoryResponse, status_code=201)
def create_repository(payload: RepositoryCreate):
    """Register a GitHub repository for analysis and trigger file ingestion."""
    try:
        repo = repository_service.create_repository(payload.github_url)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}")

    # Ingest files synchronously — runs clone, scan, and persist.
    # Errors are logged but do not fail the HTTP response; the repo row
    # is already created and the caller can query status separately.
    try:
        repository_service.ingest_repository(repo["id"])
    except Exception:
        pass  # ingest_repository never raises; this is a belt-and-suspenders guard

    # Re-fetch so the response reflects any status update from ingestion
    try:
        updated = repository_service.get_repository(repo["id"])
        if updated:
            return updated
    except Exception:
        pass

    return repo


@router.get("/{repository_id}", response_model=RepositoryResponse)
def get_repository(repository_id: str):
    """Get repository metadata and current status."""
    repo = repository_service.get_repository(repository_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo
