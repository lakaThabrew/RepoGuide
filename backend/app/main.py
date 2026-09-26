from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.api import repositories, analyses, questions, contributions, setup, files

settings = get_settings()

app = FastAPI(
    title="RepoGuide API",
    description="AI-powered developer onboarding agent",
    version="1.0.0",
)

# CORS — allow the React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(repositories.router)
app.include_router(analyses.router)
app.include_router(questions.router)
app.include_router(contributions.router)
app.include_router(setup.router)
app.include_router(files.router)


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}


@app.get("/", tags=["root"])
def root():
    return {"message": "RepoGuide API is running", "docs": "/docs"}
