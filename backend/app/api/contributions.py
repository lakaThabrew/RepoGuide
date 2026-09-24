from fastapi import APIRouter

router = APIRouter(prefix="/api/repositories", tags=["contributions"])


@router.post("/{repository_id}/contributions/generate", status_code=202)
def generate_contribution(repository_id: str):
    """
    Generate a first-contribution recommendation.
    AI integration will be implemented during the hackathon.
    """
    return {
        "message": "Contribution generation queued",
        "repository_id": repository_id,
        "status": "pending_ai_integration",
    }


@router.get("/{repository_id}/contributions")
def get_contributions(repository_id: str):
    """
    Get first-contribution recommendations for a repository.
    """
    return {
        "repository_id": repository_id,
        "title": None,
        "description": None,
        "difficulty": None,
        "why_suitable": None,
        "relevant_files": [],
        "implementation_steps": [],
        "tests_to_add": [],
        "status": "pending_ai_integration",
    }
