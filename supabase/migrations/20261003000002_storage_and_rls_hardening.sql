-- =============================================================================
-- StudySpace AI — Storage, HNSW Vector Indexing & RLS Hardening Migration
-- Migration ID: 20261003000002_storage_and_rls_hardening
-- Complies with: STUDYSPACE_AI_MASTER_ARCHITECTURE.md Sections 3, 6, 7, 10, 12
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. pgvector HNSW Index on Document Chunks
-- Uses cosine distance (vector_cosine_ops) for semantic text search
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw
    ON public.document_chunks
    USING hnsw (embedding vector_cosine_ops);

-- -----------------------------------------------------------------------------
-- 2. Automated PostgreSQL Full-Text Search Vector Update Trigger
-- Weights: 'A' for heading/title, 'B' for chunk content
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.document_chunks_search_vector_update()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('english', coalesce(NEW.heading, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(NEW.content, '')), 'B');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_document_chunks_search_vector ON public.document_chunks;
CREATE TRIGGER trg_document_chunks_search_vector
    BEFORE INSERT OR UPDATE OF heading, content ON public.document_chunks
    FOR EACH ROW
    EXECUTE FUNCTION public.document_chunks_search_vector_update();

-- -----------------------------------------------------------------------------
-- 3. Row-Level Security (RLS) Hardening for All User Entities
-- Enforces tenant isolation: User -> Workspace -> Project -> Owned Resources
-- -----------------------------------------------------------------------------

-- Message Citations
CREATE POLICY "Users can access citations in their workspaces"
    ON public.message_citations FOR ALL
    USING (
        message_id IN (
            SELECT m.id FROM public.messages m
            JOIN public.workspaces w ON m.workspace_id = w.id
            WHERE w.owner_user_id = auth.uid()
        )
    );

-- Revision Items
CREATE POLICY "Users can manage revision items in their workspaces"
    ON public.revision_items FOR ALL
    USING (
        workspace_id IN (
            SELECT id FROM public.workspaces WHERE owner_user_id = auth.uid()
        )
    );

-- Revision Item Links
CREATE POLICY "Users can manage revision links in their workspaces"
    ON public.revision_item_links FOR ALL
    USING (
        revision_item_id IN (
            SELECT r.id FROM public.revision_items r
            JOIN public.workspaces w ON r.workspace_id = w.id
            WHERE w.owner_user_id = auth.uid()
        )
    );

-- Quizzes
CREATE POLICY "Users can manage quizzes in their workspaces"
    ON public.quizzes FOR ALL
    USING (
        workspace_id IN (
            SELECT id FROM public.workspaces WHERE owner_user_id = auth.uid()
        )
    );

-- Quiz Questions
CREATE POLICY "Users can access questions for quizzes in their workspaces"
    ON public.quiz_questions FOR ALL
    USING (
        quiz_id IN (
            SELECT q.id FROM public.quizzes q
            JOIN public.workspaces w ON q.workspace_id = w.id
            WHERE w.owner_user_id = auth.uid()
        )
    );

-- Quiz Attempts
CREATE POLICY "Users can manage their own quiz attempts"
    ON public.quiz_attempts FOR ALL
    USING (
        user_id = auth.uid() AND
        workspace_id IN (
            SELECT id FROM public.workspaces WHERE owner_user_id = auth.uid()
        )
    );

-- Quiz Responses
CREATE POLICY "Users can access their own quiz responses"
    ON public.quiz_responses FOR ALL
    USING (
        quiz_attempt_id IN (
            SELECT a.id FROM public.quiz_attempts a
            WHERE a.user_id = auth.uid()
        )
    );

-- Study Guides
CREATE POLICY "Users can manage study guides in their workspaces"
    ON public.study_guides FOR ALL
    USING (
        workspace_id IN (
            SELECT id FROM public.workspaces WHERE owner_user_id = auth.uid()
        )
    );

-- Exports
CREATE POLICY "Users can manage their own exports"
    ON public.exports FOR ALL
    USING (
        user_id = auth.uid() AND
        workspace_id IN (
            SELECT id FROM public.workspaces WHERE owner_user_id = auth.uid()
        )
    );

-- API Keys
CREATE POLICY "Users can manage API keys in their workspaces"
    ON public.api_keys FOR ALL
    USING (
        workspace_id IN (
            SELECT id FROM public.workspaces WHERE owner_user_id = auth.uid()
        )
    );

-- Usage Events
CREATE POLICY "Users can view usage events in their workspaces"
    ON public.usage_events FOR SELECT
    USING (
        workspace_id IN (
            SELECT id FROM public.workspaces WHERE owner_user_id = auth.uid()
        )
    );

-- Ingestion Jobs
CREATE POLICY "Users can view ingestion jobs in their workspaces"
    ON public.ingestion_jobs FOR SELECT
    USING (
        document_id IN (
            SELECT d.id FROM public.documents d
            JOIN public.workspaces w ON d.workspace_id = w.id
            WHERE w.owner_user_id = auth.uid()
        )
    );

-- -----------------------------------------------------------------------------
-- 4. Storage Buckets and Private Object Storage Security
-- Stubs for local environment; standard Supabase Storage structures
-- -----------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS storage;

CREATE TABLE IF NOT EXISTS storage.buckets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    owner UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
    public BOOLEAN DEFAULT FALSE,
    avif_autodetection BOOLEAN DEFAULT FALSE,
    file_size_limit BIGINT,
    allowed_mime_types TEXT[]
);

CREATE TABLE IF NOT EXISTS storage.objects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bucket_id TEXT REFERENCES storage.buckets(id),
    name TEXT NOT NULL,
    owner UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
    last_accessed_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
    metadata JSONB DEFAULT '{}'::jsonb,
    path_tokens TEXT[] GENERATED ALWAYS AS (string_to_array(name, '/')) STORED
);

CREATE INDEX IF NOT EXISTS idx_storage_bucket_name ON storage.objects(bucket_id, name);

-- Register private document and export storage buckets
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES
    ('documents', 'documents', FALSE, 52428800, ARRAY['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/vnd.openxmlformats-officedocument.presentationml.presentation', 'text/plain', 'text/markdown']),
    ('exports', 'exports', FALSE, 20971520, ARRAY['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'])
ON CONFLICT (id) DO UPDATE SET
    public = EXCLUDED.public,
    file_size_limit = EXCLUDED.file_size_limit,
    allowed_mime_types = EXCLUDED.allowed_mime_types;

-- Enable RLS on storage objects
ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;

-- Storage Policy: Users can only read objects in their own workspaces (Path: workspaces/<workspace_id>/...)
CREATE POLICY "Users can access objects in their workspaces"
    ON storage.objects FOR ALL
    USING (
        bucket_id IN ('documents', 'exports') AND
        path_tokens[1] = 'workspaces' AND
        path_tokens[2]::uuid IN (
            SELECT id FROM public.workspaces WHERE owner_user_id = auth.uid()
        )
    );
