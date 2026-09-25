from fastapi import APIRouter, HTTPException
from app.schemas.analysis import AnalysisResponse, AnalysisTriggerResponse
from app.services import analysis_service
from app.services.repository_service import get_repository

router = APIRouter(prefix="/api/repositories", tags=["analyses"])


@router.post(
    "/{repository_id}/analyze",
    response_model=AnalysisTriggerResponse,
    status_code=202,
)
def start_analysis(repository_id: str):
    """
    Trigger AI analysis for a repository.

    Runs synchronously for now (background task queue added in a later task).
    Returns 404 if the repository record does not exist.
    Returns 202 with status='error' if analysis fails (error detail included).
    """
    # Validate repository exists before starting work
    try:
        repo = get_repository(repository_id)
    except Exception:
        raise HTTPException(status_code=500, detail="Database error retrieving repository.")

    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found.")

    result = analysis_service.analyse_repository(repository_id)

    if result.get("status") == "error":
        # Surface the error without leaking internals
        return AnalysisTriggerResponse(
            message="Analysis failed.",
            repository_id=repository_id,
            status="error",
            error=result.get("error", "Unknown error"),
        )

    return AnalysisTriggerResponse(
        message="Analysis complete.",
        repository_id=repository_id,
        status=result.get("status", "analyzed"),
        analysis_id=result.get("analysis_id"),
        evidence_quality=result.get("evidence_quality"),
    )


@router.get(
    "/{repository_id}/analysis",
    response_model=AnalysisResponse,
)
def get_analysis(repository_id: str):
    """
    Retrieve the stored AI analysis for a repository.
    Returns 404 if no analysis has been run yet.
    """
    # Validate repository exists
    try:
        repo = get_repository(repository_id)
    except Exception:
        raise HTTPException(status_code=500, detail="Database error retrieving repository.")

    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found.")

    row = analysis_service.get_analysis(repository_id)
    if not row:
        raise HTTPException(
            status_code=404,
            detail="No analysis found for this repository. POST /analyze to start one.",
        )

    return AnalysisResponse(
        id=row.get("id"),
        repository_id=repository_id,
        project_summary=row.get("project_summary"),
        architecture=row.get("architecture"),
        setup_guide=row.get("setup_guide"),
        important_files=row.get("important_files"),
        technologies=row.get("technologies"),
        entry_points=row.get("entry_points"),
        dependencies=row.get("dependencies"),
        created_at=row.get("created_at"),
    )
