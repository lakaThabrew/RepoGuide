# Database Design

## Tables

### repositories
Stores information about analyzed GitHub repositories.
- `id` (UUID)
- `github_url` (String)
- `status` (String)

### repository_files
Stores metadata about files within a repository.
- `repository_id` (UUID)
- `file_path` (String)
- `is_directory` (Boolean)

### analyses
Stores AI-generated analysis.
- `repository_id` (UUID)
- `project_summary` (Text)
- `architecture` (Text)
- `setup_guide` (Text)

### questions
Stores Q&A interactions.
- `repository_id` (UUID)
- `question` (Text)
- `answer` (Text)
- `referenced_files` (JSONB)

### contributions
Stores recommended first contributions.
- `repository_id` (UUID)
- `title` (Text)
- `difficulty` (Text)
