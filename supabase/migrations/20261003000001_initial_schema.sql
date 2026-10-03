-- =============================================================================
-- StudySpace AI — Initial Database Schema Migration
-- Migration ID: 20261003000001_initial_schema
-- Complies with: STUDYSPACE_AI_MASTER_ARCHITECTURE.md Section 10
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- -----------------------------------------------------------------------------
-- 0. Auth Schema Stubs (Ensures compatibility with local Docker/Postgres & Supabase)
-- -----------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS auth;
CREATE TABLE IF NOT EXISTS auth.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now())
);

CREATE OR REPLACE FUNCTION auth.uid() RETURNS uuid AS $$
    SELECT nullif(current_setting('request.jwt.claim.sub', true), '')::uuid;
$$ LANGUAGE sql STABLE;

-- -----------------------------------------------------------------------------
-- 1. Profiles (matches Supabase Auth user)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name TEXT,
    avatar_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- -----------------------------------------------------------------------------
-- 2. Workspaces
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_workspaces_owner ON public.workspaces(owner_user_id);

-- -----------------------------------------------------------------------------
-- 3. Projects
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    subject TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    archived_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_projects_workspace ON public.projects(workspace_id);
CREATE INDEX IF NOT EXISTS idx_projects_archived ON public.projects(archived_at);

-- -----------------------------------------------------------------------------
-- 4. Documents
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
    uploaded_by_user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    original_filename TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    extension TEXT NOT NULL,
    byte_size BIGINT NOT NULL,
    page_count INTEGER,
    checksum TEXT,
    document_version INTEGER NOT NULL DEFAULT 1,
    ingestion_status TEXT NOT NULL DEFAULT 'uploaded'
        CHECK (ingestion_status IN ('uploaded', 'queued', 'extracting', 'ocr_processing', 'chunking', 'embedding', 'indexed', 'failed', 'needs_attention')),
    ingestion_error_code TEXT,
    ingestion_error_message TEXT,
    parser_name TEXT,
    parser_version TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    indexed_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_documents_project ON public.documents(project_id);
CREATE INDEX IF NOT EXISTS idx_documents_workspace ON public.documents(workspace_id);
CREATE INDEX IF NOT EXISTS idx_documents_status ON public.documents(ingestion_status);
CREATE INDEX IF NOT EXISTS idx_documents_deleted ON public.documents(deleted_at);

-- -----------------------------------------------------------------------------
-- 5. Document Chunks
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES public.documents(id) ON DELETE CASCADE,
    document_version INTEGER NOT NULL DEFAULT 1,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    token_count INTEGER,
    content_hash TEXT,
    page_start INTEGER,
    page_end INTEGER,
    slide_number INTEGER,
    slide_title TEXT,
    section_path TEXT,
    heading TEXT,
    source_offsets JSONB DEFAULT '{}'::jsonb,
    search_vector TSVECTOR,
    embedding VECTOR(768),
    embedding_provider TEXT,
    embedding_model_id TEXT,
    embedding_model_version TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_chunks_doc_idx ON public.document_chunks(document_id, chunk_index);
CREATE INDEX IF NOT EXISTS idx_chunks_project ON public.document_chunks(project_id);
CREATE INDEX IF NOT EXISTS idx_chunks_workspace ON public.document_chunks(workspace_id);
CREATE INDEX IF NOT EXISTS idx_chunks_search_vector ON public.document_chunks USING GIN(search_vector);

-- -----------------------------------------------------------------------------
-- 6. Conversations
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    title TEXT NOT NULL DEFAULT 'New Conversation',
    is_pinned BOOLEAN NOT NULL DEFAULT FALSE,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'archived')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    archived_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_conversations_project ON public.conversations(project_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user ON public.conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_updated ON public.conversations(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_pinned ON public.conversations(is_pinned);

-- -----------------------------------------------------------------------------
-- 7. Messages
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES public.conversations(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    original_user_query TEXT,
    rewritten_query TEXT,
    provider TEXT,
    model_id TEXT,
    prompt_version TEXT,
    token_usage JSONB DEFAULT '{}'::jsonb,
    latency_ms INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON public.messages(conversation_id, created_at ASC);

-- -----------------------------------------------------------------------------
-- 8. Message Citations
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.message_citations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL REFERENCES public.messages(id) ON DELETE CASCADE,
    chunk_id UUID REFERENCES public.document_chunks(id) ON DELETE SET NULL,
    document_id UUID REFERENCES public.documents(id) ON DELETE SET NULL,
    source_location_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    citation_order INTEGER NOT NULL DEFAULT 1,
    validation_status TEXT NOT NULL DEFAULT 'valid' CHECK (validation_status IN ('valid', 'unverified', 'source_deleted')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_citations_message ON public.message_citations(message_id, citation_order ASC);

-- -----------------------------------------------------------------------------
-- 9. Revision Items
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.revision_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'not_started' CHECK (status IN ('not_started', 'learning', 'revised')),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_revision_project ON public.revision_items(project_id);
CREATE INDEX IF NOT EXISTS idx_revision_user ON public.revision_items(user_id);
CREATE INDEX IF NOT EXISTS idx_revision_status ON public.revision_items(status);

-- -----------------------------------------------------------------------------
-- 10. Revision Item Links
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.revision_item_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    revision_item_id UUID NOT NULL REFERENCES public.revision_items(id) ON DELETE CASCADE,
    target_type TEXT NOT NULL CHECK (target_type IN ('document', 'chunk', 'conversation', 'message', 'study_guide')),
    target_id UUID NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_rev_links_item ON public.revision_item_links(revision_item_id);

-- -----------------------------------------------------------------------------
-- 11. Quizzes
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.quizzes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
    created_by_user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    source_scope JSONB NOT NULL DEFAULT '{"type": "all"}'::jsonb,
    question_settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'ready' CHECK (status IN ('generating', 'ready', 'failed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_quizzes_project ON public.quizzes(project_id);

-- -----------------------------------------------------------------------------
-- 12. Quiz Questions
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.quiz_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quiz_id UUID NOT NULL REFERENCES public.quizzes(id) ON DELETE CASCADE,
    question_type TEXT NOT NULL CHECK (question_type IN ('mcq', 'short_answer', 'difficult')),
    difficulty TEXT NOT NULL DEFAULT 'medium' CHECK (difficulty IN ('easy', 'medium', 'hard')),
    prompt TEXT NOT NULL,
    options JSONB,
    expected_answer TEXT NOT NULL,
    explanation TEXT NOT NULL,
    source_citations JSONB DEFAULT '[]'::jsonb,
    position INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_quiz_questions_quiz ON public.quiz_questions(quiz_id, position ASC);

-- -----------------------------------------------------------------------------
-- 13. Quiz Attempts & Responses
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.quiz_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quiz_id UUID NOT NULL REFERENCES public.quizzes(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    completed_at TIMESTAMPTZ,
    score NUMERIC(5,2),
    total_questions INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_quiz_attempts_user ON public.quiz_attempts(user_id);
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_quiz ON public.quiz_attempts(quiz_id);

CREATE TABLE IF NOT EXISTS public.quiz_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quiz_attempt_id UUID NOT NULL REFERENCES public.quiz_attempts(id) ON DELETE CASCADE,
    question_id UUID NOT NULL REFERENCES public.quiz_questions(id) ON DELETE CASCADE,
    submitted_answer TEXT NOT NULL,
    is_correct BOOLEAN,
    feedback TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_quiz_responses_attempt ON public.quiz_responses(quiz_attempt_id);

-- -----------------------------------------------------------------------------
-- 14. Study Guides
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.study_guides (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
    created_by_user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    guide_type TEXT NOT NULL DEFAULT 'summary' CHECK (guide_type IN ('summary', 'key_concepts', 'formula_sheet', 'definitions')),
    source_citations JSONB DEFAULT '[]'::jsonb,
    model_metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_study_guides_project ON public.study_guides(project_id);

-- -----------------------------------------------------------------------------
-- 15. Exports
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.exports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    source_type TEXT NOT NULL CHECK (source_type IN ('response', 'conversation', 'study_guide')),
    source_id UUID NOT NULL,
    format TEXT NOT NULL CHECK (format IN ('pdf', 'docx')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    storage_path TEXT,
    page_count INTEGER,
    expires_at TIMESTAMPTZ,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_exports_user ON public.exports(user_id);
CREATE INDEX IF NOT EXISTS idx_exports_status ON public.exports(status);

-- -----------------------------------------------------------------------------
-- 16. API Keys
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
    project_id UUID REFERENCES public.projects(id) ON DELETE CASCADE,
    created_by_user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    key_prefix TEXT NOT NULL,
    key_hash TEXT NOT NULL,
    scopes JSONB NOT NULL DEFAULT '["chat"]'::jsonb,
    rate_limit_policy JSONB NOT NULL DEFAULT '{"rpm": 60}'::jsonb,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'revoked')),
    last_used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    revoked_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_api_keys_hash ON public.api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON public.api_keys(key_prefix);
CREATE INDEX IF NOT EXISTS idx_api_keys_workspace ON public.api_keys(workspace_id);

-- -----------------------------------------------------------------------------
-- 17. Usage Events
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.usage_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
    api_key_id UUID REFERENCES public.api_keys(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,
    model_provider TEXT,
    model_id TEXT,
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    latency_ms INTEGER,
    status_code INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_usage_events_workspace ON public.usage_events(workspace_id, created_at DESC);

-- -----------------------------------------------------------------------------
-- 18. Ingestion Jobs
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.ingestion_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES public.documents(id) ON DELETE CASCADE,
    document_version INTEGER NOT NULL DEFAULT 1,
    job_type TEXT NOT NULL DEFAULT 'full_ingestion',
    status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued', 'running', 'completed', 'failed', 'retrying')),
    attempt_count INTEGER NOT NULL DEFAULT 0,
    stage TEXT NOT NULL DEFAULT 'queued',
    progress_metadata JSONB DEFAULT '{}'::jsonb,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    error_code TEXT,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_doc ON public.ingestion_jobs(document_id);
CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_status ON public.ingestion_jobs(status);

-- -----------------------------------------------------------------------------
-- Row Level Security (RLS) Enablement
-- -----------------------------------------------------------------------------
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.workspaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.document_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.message_citations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.revision_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.revision_item_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.quizzes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.quiz_questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.quiz_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.quiz_responses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.study_guides ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.exports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.usage_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ingestion_jobs ENABLE ROW LEVEL SECURITY;

-- -----------------------------------------------------------------------------
-- RLS Baseline Policies (User-scoped access)
-- -----------------------------------------------------------------------------
CREATE POLICY "Users can manage their own profile"
    ON public.profiles FOR ALL
    USING (auth.uid() = id);

CREATE POLICY "Users can manage their own workspaces"
    ON public.workspaces FOR ALL
    USING (auth.uid() = owner_user_id);

CREATE POLICY "Users can access projects in their workspaces"
    ON public.projects FOR ALL
    USING (
        workspace_id IN (
            SELECT id FROM public.workspaces WHERE owner_user_id = auth.uid()
        )
    );

CREATE POLICY "Users can access documents in their workspaces"
    ON public.documents FOR ALL
    USING (
        workspace_id IN (
            SELECT id FROM public.workspaces WHERE owner_user_id = auth.uid()
        )
    );

CREATE POLICY "Users can access chunks in their workspaces"
    ON public.document_chunks FOR ALL
    USING (
        workspace_id IN (
            SELECT id FROM public.workspaces WHERE owner_user_id = auth.uid()
        )
    );

CREATE POLICY "Users can access conversations in their workspaces"
    ON public.conversations FOR ALL
    USING (
        workspace_id IN (
            SELECT id FROM public.workspaces WHERE owner_user_id = auth.uid()
        )
    );

CREATE POLICY "Users can access messages in their workspaces"
    ON public.messages FOR ALL
    USING (
        workspace_id IN (
            SELECT id FROM public.workspaces WHERE owner_user_id = auth.uid()
        )
    );
