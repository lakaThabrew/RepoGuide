-- RepoGuide Supabase Database Schema

-- 1. repositories Table
create table repositories (
    id uuid primary key default gen_random_uuid(),
    github_url text not null,
    owner text,
    name text,
    description text,
    default_branch text,
    language text,
    status text default 'pending',
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

-- 2. repository_files Table
create table repository_files (
    id uuid primary key default gen_random_uuid(),
    repository_id uuid
        references repositories(id)
        on delete cascade,
    file_path text not null,
    file_name text,
    extension text,
    language text,
    file_size integer,
    is_directory boolean default false,
    created_at timestamptz default now()
);

-- 3. analyses Table
create table analyses (
    id uuid primary key default gen_random_uuid(),
    repository_id uuid
        references repositories(id)
        on delete cascade,
    project_summary text,
    architecture text,
    setup_guide text,
    important_files jsonb,
    technologies jsonb,
    entry_points jsonb,
    dependencies jsonb,
    created_at timestamptz default now()
);

-- 4. questions Table
create table questions (
    id uuid primary key default gen_random_uuid(),
    repository_id uuid
        references repositories(id)
        on delete cascade,
    question text not null,
    answer text,
    referenced_files jsonb,
    created_at timestamptz default now()
);

-- 5. contributions Table
create table contributions (
    id uuid primary key default gen_random_uuid(),
    repository_id uuid
        references repositories(id)
        on delete cascade,
    title text,
    description text,
    difficulty text,
    why_suitable text,
    relevant_files jsonb,
    implementation_steps jsonb,
    tests_to_add jsonb,
    created_at timestamptz default now()
);
