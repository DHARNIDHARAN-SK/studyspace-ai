from pathlib import Path


def test_initial_migration_exists_and_valid():
    repo_root = Path(__file__).resolve().parents[3]
    migration_file = repo_root / "supabase" / "migrations" / "20261003000001_initial_schema.sql"

    assert migration_file.exists(), f"Migration file not found at {migration_file}"
    content = migration_file.read_text(encoding="utf-8")

    # Check key tables required by master architecture Section 10
    required_tables = [
        "profiles",
        "workspaces",
        "projects",
        "documents",
        "document_chunks",
        "conversations",
        "messages",
        "message_citations",
        "revision_items",
        "revision_item_links",
        "quizzes",
        "quiz_questions",
        "quiz_attempts",
        "quiz_responses",
        "study_guides",
        "exports",
        "api_keys",
        "usage_events",
        "ingestion_jobs",
    ]

    for table in required_tables:
        assert f"CREATE TABLE IF NOT EXISTS public.{table}" in content, f"Table {table} missing from migration"

    # Check pgvector extension and embedding vector column
    assert 'CREATE EXTENSION IF NOT EXISTS "vector"' in content
    assert "embedding VECTOR(768)" in content

    # Check Row Level Security
    assert "ENABLE ROW LEVEL SECURITY" in content
