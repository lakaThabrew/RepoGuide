from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/repositories", tags=["questions"])


class QuestionRequest(BaseModel):
    question: str


@router.post("/{repository_id}/questions")
def ask_question(repository_id: str, payload: QuestionRequest):
    """
    Ask a question about a repository.
    AI answer generation will be implemented during the hackathon.
    """
    return {
        "repository_id": repository_id,
        "question": payload.question,
        "answer": None,
        "referenced_files": [],
        "status": "pending_ai_integration",
    }
