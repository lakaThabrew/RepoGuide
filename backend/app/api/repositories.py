from fastapi import APIRouter, HTTPException
from app.schemas.repository import RepositoryCreate, RepositoryResponse
from app.services import repository_service

router = APIRouter(prefix="/api/repositories", tags=["repositories"])


@router.post("", response_model=RepositoryResponse, status_code=201)
def create_repository(payload: RepositoryCreate):
    """Register a GitHub repository for analysis."""
    try:
        repo = repository_service.create_repository(payload.github_url)
        return repo
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}")


@router.get("/{repository_id}", response_model=RepositoryResponse)
def get_repository(repository_id: str):
    """Get repository metadata and current status."""
    repo = repository_service.get_repository(repository_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo
