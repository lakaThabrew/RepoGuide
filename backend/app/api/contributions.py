"""
contributions.py — API endpoints for first-contribution recommendations.

GET  /api/repositories/{repository_id}/contributions
  Returns stored or freshly generated contribution recommendations.

POST /api/repositories/{repository_id}/contributions/generate
  (Re)generates contribution recommendations from current analysis.

Errors:
  404 — repository not found, or analysis not found
  422 — insufficient evidence
  500 — internal database errors (never exposes stack traces)
"""

from fastapi import APIRouter, HTTPException
from app.schemas.contribution import ContributionResponse, ContributionGenerateResponse
from app.services import contribution_service
from app.services.repository_service import get_repository

router = APIRouter(prefix="/api/repositories", tags=["contributions"])


@router.post(
    "/{repository_id}/contributions/generate",
    response_model=ContributionGenerateResponse,
    status_code=202,
)
def generate_contribution(repository_id: str) -> ContributionGenerateResponse:
    """
    (Re)generate first-contribution recommendations for a repository.

    Runs the deterministic contribution engine against the stored analysis.
    Persists the result for future GET requests.

    Returns 404 if the repository or analysis is not found.
    Returns 422 if there is insufficient evidence to make recommendations.
    """
    # Validate repository exists
    try:
        repo = get_repository(repository_id)
    except Exception:
        raise HTTPException(status_code=500, detail="Database error retrieving repository.")

    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found.")

    result = contribution_service.generate_contributions(repository_id)

    if result.status == "error":
        error_msg = result.error or "Unknown error"
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg)
        raise HTTPException(status_code=500, detail="Internal error. Please try again.")

    if result.status == "no_analysis":
        raise HTTPException(
            status_code=404,
            detail=result.error or "No analysis found. Run analysis before generating contributions.",
        )

    if result.status == "insufficient_evidence":
        raise HTTPException(
            status_code=422,
            detail=result.error or "Insufficient repository evidence to generate contributions.",
        )

    return ContributionGenerateResponse(
        message="Contribution analysis complete.",
        repository_id=repository_id,
        status="ok",
        candidates_count=len(result.candidates),
    )


@router.get(
    "/{repository_id}/contributions",
    response_model=ContributionResponse,
)
def get_contributions(repository_id: str) -> ContributionResponse:
    """
    Get first-contribution recommendations for a repository.

    Returns previously generated recommendations if available,
    otherwise generates them from the stored analysis.

    Returns 404 if repository or analysis not found.
    Returns 422 if there is insufficient evidence.
    """
    # Validate repository exists
    try:
        repo = get_repository(repository_id)
    except Exception:
        raise HTTPException(status_code=500, detail="Database error retrieving repository.")

    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found.")

    result = contribution_service.get_contributions(repository_id)

    if result.status == "error":
        error_msg = result.error or "Unknown error"
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg)
        raise HTTPException(status_code=500, detail="Internal error. Please try again.")

    if result.status == "no_analysis":
        raise HTTPException(
            status_code=404,
            detail=result.error or "No analysis found. Run analysis before finding contributions.",
        )

    if result.status == "insufficient_evidence":
        raise HTTPException(
            status_code=422,
            detail=result.error or "Insufficient repository evidence to generate contributions.",
        )

    return result
