-- =============================================================================
-- StudySpace AI — Migration 000003: Phase 8 Conversational RAG & Multi-Query
-- Adds observability, query transformation, and semantic cache metadata to messages
-- =============================================================================

ALTER TABLE public.messages
    ADD COLUMN IF NOT EXISTS selected_query TEXT,
    ADD COLUMN IF NOT EXISTS rewrite_enabled BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS rewrite_accepted BOOLEAN,
    ADD COLUMN IF NOT EXISTS multi_query_enabled BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS generated_queries JSONB DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS cache_hit BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS rag_metadata JSONB DEFAULT '{}'::jsonb;

-- Index on conversation messages created_at for fast conversation history fetching
CREATE INDEX IF NOT EXISTS idx_messages_conversation_created 
    ON public.messages(conversation_id, created_at ASC);
