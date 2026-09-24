from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime


class RepositoryCreate(BaseModel):
    github_url: str


class RepositoryResponse(BaseModel):
    id: str
    github_url: str
    owner: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    default_branch: Optional[str] = None
    language: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
