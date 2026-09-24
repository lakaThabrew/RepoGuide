from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/repositories", tags=["analyses"])


@router.post("/{repository_id}/analyze", status_code=202)
def start_analysis(repository_id: str):
    """
    Trigger AI analysis for a repository.
    AI integration will be implemented during the hackathon.
    """
    return {
        "message": "Analysis queued",
        "repository_id": repository_id,
        "status": "analyzing",
    }


@router.get("/{repository_id}/analysis")
def get_analysis(repository_id: str):
    """
    Retrieve AI analysis for a repository.
    Returns a placeholder until hackathon AI integration is complete.
    """
    return {
        "repository_id": repository_id,
        "project_summary": None,
        "architecture": None,
        "setup_guide": None,
        "important_files": [],
        "technologies": [],
        "entry_points": [],
        "dependencies": [],
        "status": "pending_ai_integration",
    }
