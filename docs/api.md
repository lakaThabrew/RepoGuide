# API Documentation

## Repositories
- `POST /api/repositories`: Analyze a repository. Requires `github_url`. Returns repository ID and status.
- `GET /api/repositories/{repository_id}`: Get repository status.

## Analysis
- `POST /api/repositories/{repository_id}/analyze`: Trigger analysis.
- `GET /api/repositories/{repository_id}/analysis`: Get project summary, architecture, important files.

## Q&A
- `POST /api/repositories/{repository_id}/questions`: Ask a question about the repository. Returns answer and referenced files.

## Contributions
- `POST /api/repositories/{repository_id}/contributions/generate`: Generate a first contribution.
- `GET /api/repositories/{repository_id}/contributions`: Retrieve generated contributions.
