"""
setup.py — API endpoints for the Repository Setup Assistant.

GET  /api/repositories/{repository_id}/setup
  Returns a previously generated setup guide (or generates one if none exists).

POST /api/repositories/{repository_id}/setup/generate
  (Re)generates the setup guide from the current stored analysis.

Errors:
  404 — repository not found, or analysis not found
  422 — insufficient evidence to generate a guide
  500 — internal database errors (stack traces never exposed)
"""

from fastapi import APIRouter, HTTPException
from app.schemas.setup import SetupGuideResponse, SetupGenerateResponse
from app.services import setup_service
from app.services.repository_service import get_repository

router = APIRouter(prefix="/api/repositories", tags=["setup"])


@router.post(
    "/{repository_id}/setup/generate",
    response_model=SetupGenerateResponse,
    status_code=202,
)
def generate_setup(repository_id: str) -> SetupGenerateResponse:
    """
    (Re)generate the setup guide for a repository.

    Runs the deterministic setup engine against the stored analysis.
    Persists the result into analyses.setup_guide for future GET requests.

    Returns 404 if the repository or analysis is not found.
    Returns 422 if there is insufficient evidence to produce a guide.
    """
    # Validate repository exists
    try:
        repo = get_repository(repository_id)
    except Exception:
        raise HTTPException(status_code=500, detail="Database error retrieving repository.")

    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found.")

    result = setup_service.generate_setup_guide(repository_id)

    if result.status == "error":
        error_msg = result.error or "Unknown error"
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg)
        raise HTTPException(status_code=500, detail="Internal error. Please try again.")

    if result.status == "no_analysis":
        raise HTTPException(
            status_code=404,
            detail=result.error or "No analysis found. Run analysis before generating a setup guide.",
        )

    if result.status == "insufficient_evidence":
        raise HTTPException(
            status_code=422,
            detail=result.error or "Insufficient repository evidence to generate a setup guide.",
        )

    guide = result.guide
    return SetupGenerateResponse(
        message="Setup guide generated.",
        repository_id=repository_id,
        status="ok",
        confidence=guide.confidence if guide else None,
        warnings_count=len(guide.warnings) if guide else 0,
    )


@router.get(
    "/{repository_id}/setup",
    response_model=SetupGuideResponse,
)
def get_setup(repository_id: str) -> SetupGuideResponse:
    """
    Get the setup guide for a repository.

    Returns a previously generated guide if available,
    otherwise generates one from the stored analysis.

    Returns 404 if the repository or analysis is not found.
    Returns 422 if there is insufficient evidence.
    """
    # Validate repository exists
    try:
        repo = get_repository(repository_id)
    except Exception:
        raise HTTPException(status_code=500, detail="Database error retrieving repository.")

    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found.")

    result = setup_service.get_setup_guide(repository_id)

    if result.status == "error":
        error_msg = result.error or "Unknown error"
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg)
        raise HTTPException(status_code=500, detail="Internal error. Please try again.")

    if result.status == "no_analysis":
        raise HTTPException(
            status_code=404,
            detail=result.error or "No analysis found. Run analysis before generating a setup guide.",
        )

    if result.status == "insufficient_evidence":
        raise HTTPException(
            status_code=422,
            detail=result.error or "Insufficient repository evidence to generate a setup guide.",
        )

    return result
