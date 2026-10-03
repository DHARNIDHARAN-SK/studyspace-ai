from dataclasses import dataclass, field
import time
from typing import Any, Dict, List, Optional
import uuid

from app.core.config import settings
from app.core.logging import logger
from app.rag.cache.redis_cache import RedisSemanticCache, SemanticCacheHit
from app.rag.context.builder import ContextBuilder
from app.rag.context.models import CitationSource
from app.rag.conversation.context_manager import (
    ConversationContextManager,
    ConversationTurn,
)
from app.rag.embeddings.base import BaseEmbeddingProvider
from app.rag.embeddings.registry import get_embedding_provider
from app.rag.llm.base import BaseLLMProvider
from app.rag.llm.registry import get_llm_provider
from app.rag.prompts.baseline_rag import (
    BASELINE_RAG_SYSTEM_PROMPT,
    build_baseline_rag_prompt,
)
from app.rag.prompts.conversational_rag import (
    CONVERSATIONAL_RAG_SYSTEM_PROMPT,
    build_conversational_rag_prompt,
)
from app.rag.retrieval.hybrid_retriever import HybridRetrievalResult, HybridRetriever
from app.rag.retrieval.models import RetrievedChunk
from app.rag.retrieval.multi_query_retriever import (
    MultiQueryRetrievalResult,
    MultiQueryRetriever,
)
from app.rag.retrieval.vector_retriever import VectorRetriever
from app.rag.rewriting.service import (
    QueryTransformationService,
    RewrittenQueryResult,
)


@dataclass
class BaselineRAGResult:
    """End-to-end outcome of baseline RAG query processing."""
    query: str
    answer: str
    citations: List[CitationSource]
    retrieved_chunks: List[RetrievedChunk]
    llm_model: str
    embedding_model: str
    provider: str
    total_latency_ms: int
    retrieval_latency_ms: int
    generation_latency_ms: int
    token_usage: Dict[str, Any] = field(default_factory=dict)
    retrieval_mode: str = "baseline"


@dataclass
class AdvancedRAGResult:
    """End-to-end outcome of Phase 7 Advanced Hybrid RAG query processing."""
    query: str
    answer: str
    citations: List[CitationSource]
    retrieved_chunks: List[RetrievedChunk]
    llm_model: str
    embedding_model: str
    provider: str
    total_latency_ms: int
    retrieval_latency_ms: int
    generation_latency_ms: int
    dense_latency_ms: int = 0
    lexical_latency_ms: int = 0
    fusion_latency_ms: int = 0
    rerank_latency_ms: int = 0
    dense_candidates_count: int = 0
    lexical_candidates_count: int = 0
    fused_candidates_count: int = 0
    token_usage: Dict[str, Any] = field(default_factory=dict)
    retrieval_mode: str = "advanced"


@dataclass
class ConversationalRAGResult:
    """End-to-end outcome of Phase 8 Conversational RAG with query rewriting and multi-query."""
    query: str
    selected_query: str
    answer: str
    citations: List[CitationSource]
    retrieved_chunks: List[RetrievedChunk]
    llm_model: str
    embedding_model: str
    provider: str
    total_latency_ms: int
    retrieval_latency_ms: int
    generation_latency_ms: int
    rewrite_latency_ms: int = 0
    cache_latency_ms: int = 0
    rewrite_enabled: bool = False
    rewrite_accepted: bool = False
    rewritten_query: Optional[str] = None
    multi_query_enabled: bool = False
    generated_queries: List[str] = field(default_factory=list)
    cache_hit: bool = False
    cached_query: Optional[str] = None
    similarity_score: Optional[float] = None
    token_usage: Dict[str, Any] = field(default_factory=dict)
    retrieval_mode: str = "conversational"
    rag_metadata: Dict[str, Any] = field(default_factory=dict)


class BaselineRAGPipeline:
    """
    Phase 6 Baseline RAG execution:
    User Query -> Query Embedding -> pgvector Cosine Search -> Top-K Chunks ->
    Context Construction -> phi4-mini Prompt Completion -> Grounded Answer with Citations.
    """

    def __init__(
        self,
        retriever: Optional[VectorRetriever] = None,
        context_builder: Optional[ContextBuilder] = None,
        llm_provider: Optional[BaseLLMProvider] = None,
        embedding_provider: Optional[BaseEmbeddingProvider] = None,
    ):
        self.embedding_provider = embedding_provider or get_embedding_provider()
        self.retriever = retriever or VectorRetriever(embedding_provider=self.embedding_provider)
        self.context_builder = context_builder or ContextBuilder()
        self.llm_provider = llm_provider or get_llm_provider()

    async def execute(
        self,
        query: str,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        top_k: int = settings.RAG_DEFAULT_TOP_K,
        document_ids: Optional[List[uuid.UUID]] = None,
        temperature: float = 0.1,
    ) -> BaselineRAGResult:
        pipeline_start = time.time()

        # 1. Vector Retrieval
        retrieval_start = time.time()
        retrieved_chunks = await self.retriever.retrieve(
            query=query,
            workspace_id=workspace_id,
            project_id=project_id,
            top_k=top_k,
            document_ids=document_ids,
        )
        retrieval_latency_ms = int((time.time() - retrieval_start) * 1000)

        # 2. Context & Citation Construction
        context_result = self.context_builder.build_context(retrieved_chunks)

        # 3. Prompt Construction
        user_prompt = build_baseline_rag_prompt(query, context_result.context_text)

        # 4. LLM Generation
        generation_start = time.time()
        llm_response = await self.llm_provider.generate(
            prompt=user_prompt,
            system_prompt=BASELINE_RAG_SYSTEM_PROMPT,
            temperature=temperature,
        )
        generation_latency_ms = int((time.time() - generation_start) * 1000)
        total_latency_ms = int((time.time() - pipeline_start) * 1000)

        token_usage = {
            "prompt_tokens": llm_response.prompt_tokens,
            "completion_tokens": llm_response.completion_tokens,
        }

        logger.info(
            "Baseline RAG executed (total_latency=%dms, retrieved=%d, context_chars=%d, model=%s)",
            total_latency_ms,
            len(retrieved_chunks),
            context_result.total_chars,
            llm_response.model,
        )

        return BaselineRAGResult(
            query=query,
            answer=llm_response.content,
            citations=context_result.citations,
            retrieved_chunks=retrieved_chunks,
            llm_model=llm_response.model,
            embedding_model=self.embedding_provider.model_id,
            provider=llm_response.provider,
            total_latency_ms=total_latency_ms,
            retrieval_latency_ms=retrieval_latency_ms,
            generation_latency_ms=generation_latency_ms,
            token_usage=token_usage,
            retrieval_mode="baseline",
        )


class AdvancedRAGPipeline:
    """
    Phase 7 Advanced RAG execution:
    User Query -> Parallel Dense (pgvector HNSW) + Lexical (PostgreSQL tsvector FTS) ->
    Candidate Fusion (RRF) -> Local Cross-Encoder Reranking -> Top Relevant Chunks ->
    Context Construction -> phi4-mini Prompt Completion -> Grounded Answer with Citations.
    """

    def __init__(
        self,
        retriever: Optional[HybridRetriever] = None,
        context_builder: Optional[ContextBuilder] = None,
        llm_provider: Optional[BaseLLMProvider] = None,
        embedding_provider: Optional[BaseEmbeddingProvider] = None,
    ):
        self.embedding_provider = embedding_provider or get_embedding_provider()
        self.retriever = retriever or HybridRetriever()
        self.context_builder = context_builder or ContextBuilder()
        self.llm_provider = llm_provider or get_llm_provider()

    async def execute(
        self,
        query: str,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        dense_top_k: int = settings.RAG_DENSE_TOP_K,
        lexical_top_k: int = settings.RAG_LEXICAL_TOP_K,
        final_top_k: int = settings.RAG_RERANK_TOP_N,
        document_ids: Optional[List[uuid.UUID]] = None,
        temperature: float = 0.1,
    ) -> AdvancedRAGResult:
        pipeline_start = time.time()

        # 1. Parallel Hybrid Retrieval + Fusion + Reranking
        retrieval_result: HybridRetrievalResult = await self.retriever.retrieve_detailed(
            query=query,
            workspace_id=workspace_id,
            project_id=project_id,
            dense_top_k=dense_top_k,
            lexical_top_k=lexical_top_k,
            final_top_k=final_top_k,
            document_ids=document_ids,
        )

        # 2. Context & Citation Construction
        context_result = self.context_builder.build_context(retrieval_result.chunks)

        # 3. Prompt Construction
        user_prompt = build_baseline_rag_prompt(query, context_result.context_text)

        # 4. LLM Generation
        generation_start = time.time()
        llm_response = await self.llm_provider.generate(
            prompt=user_prompt,
            system_prompt=BASELINE_RAG_SYSTEM_PROMPT,
            temperature=temperature,
        )
        generation_latency_ms = int((time.time() - generation_start) * 1000)
        total_latency_ms = int((time.time() - pipeline_start) * 1000)

        token_usage = {
            "prompt_tokens": llm_response.prompt_tokens,
            "completion_tokens": llm_response.completion_tokens,
        }

        logger.info(
            "Advanced RAG executed (total=%dms, retrieval=%dms [dense=%dms, lex=%dms, rrf=%dms, rerank=%dms], generation=%dms, chunks=%d, model=%s)",
            total_latency_ms,
            retrieval_result.total_latency_ms,
            retrieval_result.dense_latency_ms,
            retrieval_result.lexical_latency_ms,
            retrieval_result.fusion_latency_ms,
            retrieval_result.rerank_latency_ms,
            generation_latency_ms,
            len(retrieval_result.chunks),
            llm_response.model,
        )

        return AdvancedRAGResult(
            query=query,
            answer=llm_response.content,
            citations=context_result.citations,
            retrieved_chunks=retrieval_result.chunks,
            llm_model=llm_response.model,
            embedding_model=self.embedding_provider.model_id,
            provider=llm_response.provider,
            total_latency_ms=total_latency_ms,
            retrieval_latency_ms=retrieval_result.total_latency_ms,
            generation_latency_ms=generation_latency_ms,
            dense_latency_ms=retrieval_result.dense_latency_ms,
            lexical_latency_ms=retrieval_result.lexical_latency_ms,
            fusion_latency_ms=retrieval_result.fusion_latency_ms,
            rerank_latency_ms=retrieval_result.rerank_latency_ms,
            dense_candidates_count=len(retrieval_result.dense_candidates),
            lexical_candidates_count=len(retrieval_result.lexical_candidates),
            fused_candidates_count=len(retrieval_result.fused_candidates),
            token_usage=token_usage,
            retrieval_mode="advanced",
        )


class ConversationalRAGPipeline:
    """
    Phase 8 Conversational RAG execution:
    User Query -> Deduplication / Semantic Cache Check ->
    Contextual Query Rewriting / Sub-Query Decomposition / Multi-Query Expansion ->
    Parallel Multi-Query Hybrid Retrieval -> Candidate Deduplication ->
    Cross-Encoder Reranking -> Context & Bounded History Fusion ->
    phi4-mini Prompt Completion -> Semantic Cache Storage -> Grounded Answer.
    """

    def __init__(
        self,
        retriever: Optional[MultiQueryRetriever] = None,
        context_builder: Optional[ContextBuilder] = None,
        llm_provider: Optional[BaseLLMProvider] = None,
        embedding_provider: Optional[BaseEmbeddingProvider] = None,
        transformation_service: Optional[QueryTransformationService] = None,
        cache: Optional[RedisSemanticCache] = None,
    ):
        self.embedding_provider = embedding_provider or get_embedding_provider()
        self.retriever = retriever or MultiQueryRetriever()
        self.context_builder = context_builder or ContextBuilder()
        self.llm_provider = llm_provider or get_llm_provider()
        self.transformation_service = transformation_service or QueryTransformationService(llm_provider=self.llm_provider)
        self.cache = cache or RedisSemanticCache(embedding_provider=self.embedding_provider)

    async def execute(
        self,
        query: str,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        history: Optional[List[ConversationTurn]] = None,
        rewrite_enabled: bool = settings.RAG_QUERY_REWRITE_ENABLED,
        selected_query: Optional[str] = None,
        rewrite_accepted: Optional[bool] = None,
        multi_query_enabled: bool = settings.RAG_MULTI_QUERY_ENABLED,
        decomposition_enabled: bool = settings.RAG_DECOMPOSITION_ENABLED,
        dense_top_k: int = settings.RAG_DENSE_TOP_K,
        lexical_top_k: int = settings.RAG_LEXICAL_TOP_K,
        final_top_k: int = settings.RAG_RERANK_TOP_N,
        document_ids: Optional[List[uuid.UUID]] = None,
        temperature: float = 0.1,
    ) -> ConversationalRAGResult:
        pipeline_start = time.time()
        clean_query = query.strip()
        history_list = history or []

        # 1. Semantic Cache Lookup (Tenant-isolated)
        cache_start = time.time()
        cached_hit: Optional[SemanticCacheHit] = await self.cache.lookup(
            workspace_id=workspace_id,
            project_id=project_id,
            query=clean_query,
        )
        cache_latency_ms = int((time.time() - cache_start) * 1000)

        if cached_hit:
            total_latency_ms = int((time.time() - pipeline_start) * 1000)
            # Reconstruct CitationSource and RetrievedChunk objects
            cached_citations = [
                CitationSource(
                    document_id=uuid.UUID(c["document_id"]) if c.get("document_id") else uuid.uuid4(),
                    document_filename=c.get("document_filename", ""),
                    chunk_id=uuid.UUID(c["chunk_id"]) if c.get("chunk_id") else uuid.uuid4(),
                    page_start=c.get("page_start"),
                    page_end=c.get("page_end"),
                    slide_number=c.get("slide_number"),
                    section_path=c.get("section_path"),
                    similarity_score=float(c.get("similarity_score", 1.0)),
                    citation_label=c.get("citation_label", ""),
                    snippet=c.get("snippet", ""),
                )
                for c in cached_hit.citations
            ]
            cached_chunks = [
                RetrievedChunk(
                    chunk_id=uuid.UUID(chk["chunk_id"]) if chk.get("chunk_id") else uuid.uuid4(),
                    document_id=uuid.UUID(chk["document_id"]) if chk.get("document_id") else uuid.uuid4(),
                    document_filename=chk.get("document_filename", ""),
                    workspace_id=uuid.UUID(chk["workspace_id"]) if chk.get("workspace_id") else workspace_id,
                    project_id=uuid.UUID(chk["project_id"]) if chk.get("project_id") else project_id,
                    chunk_index=chk.get("chunk_index", 0),
                    content=chk.get("content", ""),
                    token_count=chk.get("token_count"),
                    page_start=chk.get("page_start"),
                    page_end=chk.get("page_end"),
                    slide_number=chk.get("slide_number"),
                    slide_title=chk.get("slide_title"),
                    section_path=chk.get("section_path"),
                    heading=chk.get("heading"),
                    similarity_score=float(chk.get("similarity_score", 1.0)),
                    retrieval_method=chk.get("retrieval_method", "semantic_cache"),
                )
                for chk in cached_hit.retrieved_chunks
            ]

            return ConversationalRAGResult(
                query=clean_query,
                selected_query=clean_query,
                answer=cached_hit.answer,
                citations=cached_citations,
                retrieved_chunks=cached_chunks,
                llm_model=self.llm_provider.model_id,
                embedding_model=self.embedding_provider.model_id,
                provider=self.llm_provider.provider_name,
                total_latency_ms=total_latency_ms,
                retrieval_latency_ms=0,
                generation_latency_ms=0,
                rewrite_latency_ms=0,
                cache_latency_ms=cache_latency_ms,
                rewrite_enabled=rewrite_enabled,
                rewrite_accepted=False,
                rewritten_query=None,
                multi_query_enabled=multi_query_enabled,
                generated_queries=[],
                cache_hit=True,
                cached_query=cached_hit.cached_query,
                similarity_score=cached_hit.similarity_score,
                token_usage={},
                retrieval_mode="conversational",
                rag_metadata={"cache_matched_query": cached_hit.cached_query, "cache_similarity": cached_hit.similarity_score},
            )

        # 2. Request Deduplication Lock
        dedup_token = await self.cache.acquire_dedup_lock(workspace_id, project_id, clean_query)

        try:
            # 3. Query Rewriting & Formulation
            rewrite_latency_ms = 0
            rewritten_text: Optional[str] = None
            active_search_query = clean_query

            if selected_query:
                # Student explicitly provided or confirmed the rewritten query
                active_search_query = selected_query.strip()
                is_accepted = rewrite_accepted if rewrite_accepted is not None else True
            elif rewrite_enabled and history_list:
                rewrite_start = time.time()
                rw_res: RewrittenQueryResult = await self.transformation_service.rewrite_query(
                    query=clean_query,
                    history=history_list,
                )
                rewrite_latency_ms = rw_res.latency_ms
                if rw_res.was_rewritten:
                    rewritten_text = rw_res.rewritten_query
                    active_search_query = rewritten_text
                    is_accepted = True
                else:
                    is_accepted = False
            else:
                is_accepted = False

            # 4. Multi-Query Expansion / Query Decomposition
            generated_queries: List[str] = []
            if decomposition_enabled:
                generated_queries = await self.transformation_service.decompose_query(active_search_query)
            elif multi_query_enabled:
                generated_queries = await self.transformation_service.generate_multi_queries(
                    active_search_query,
                    count=settings.RAG_MULTI_QUERY_COUNT,
                )

            search_query_pool = generated_queries if generated_queries else [active_search_query]

            # 5. Parallel Multi-Query Hybrid Retrieval
            retrieval_start = time.time()
            retrieval_outcome: MultiQueryRetrievalResult = await self.retriever.retrieve(
                queries=search_query_pool,
                primary_query=active_search_query,
                workspace_id=workspace_id,
                project_id=project_id,
                dense_top_k=dense_top_k,
                lexical_top_k=lexical_top_k,
                final_top_k=final_top_k,
                document_ids=document_ids,
            )
            retrieval_latency_ms = int((time.time() - retrieval_start) * 1000)

            # 6. Context Construction
            context_result = self.context_builder.build_context(retrieval_outcome.chunks)
            history_text = ConversationContextManager.format_history_for_prompt(history_list)

            # 7. Prompt Construction & Generation
            user_prompt = build_conversational_rag_prompt(
                query=active_search_query,
                context_text=context_result.context_text,
                history_text=history_text,
            )

            generation_start = time.time()
            llm_response = await self.llm_provider.generate(
                prompt=user_prompt,
                system_prompt=CONVERSATIONAL_RAG_SYSTEM_PROMPT,
                temperature=temperature,
            )
            generation_latency_ms = int((time.time() - generation_start) * 1000)
            total_latency_ms = int((time.time() - pipeline_start) * 1000)

            token_usage = {
                "prompt_tokens": llm_response.prompt_tokens,
                "completion_tokens": llm_response.completion_tokens,
            }

            # 8. Store in Semantic Cache
            citation_dicts = [
                {
                    "document_id": str(c.document_id),
                    "document_filename": c.document_filename,
                    "chunk_id": str(c.chunk_id) if c.chunk_id else None,
                    "page_start": c.page_start,
                    "page_end": c.page_end,
                    "slide_number": c.slide_number,
                    "section_path": c.section_path,
                    "snippet": c.snippet,
                    "similarity_score": c.similarity_score,
                    "citation_label": c.citation_label,
                }
                for c in context_result.citations
            ]
            chunk_dicts = [
                {
                    "chunk_id": str(chk.chunk_id),
                    "document_id": str(chk.document_id),
                    "document_filename": chk.document_filename,
                    "workspace_id": str(chk.workspace_id),
                    "project_id": str(chk.project_id),
                    "chunk_index": chk.chunk_index,
                    "content": chk.content,
                    "token_count": chk.token_count,
                    "page_start": chk.page_start,
                    "page_end": chk.page_end,
                    "slide_number": chk.slide_number,
                    "slide_title": chk.slide_title,
                    "section_path": chk.section_path,
                    "heading": chk.heading,
                    "similarity_score": chk.similarity_score,
                    "retrieval_method": chk.retrieval_method,
                }
                for chk in retrieval_outcome.chunks
            ]

            await self.cache.store(
                workspace_id=workspace_id,
                project_id=project_id,
                query=clean_query,
                answer=llm_response.content,
                citations=citation_dicts,
                retrieved_chunks=chunk_dicts,
                metadata={
                    "selected_query": active_search_query,
                    "rewritten_query": rewritten_text,
                    "generated_queries": generated_queries,
                },
            )

            rag_meta = {
                "total_candidates": retrieval_outcome.total_candidates,
                "deduplicated_candidates": retrieval_outcome.deduplicated_candidates,
                "per_query_counts": retrieval_outcome.per_query_counts,
                "retrieval_queries": search_query_pool,
            }

            logger.info(
                "Conversational RAG executed: total=%dms (cache=%dms, rewrite=%dms, ret=%dms, gen=%dms), chunks=%d, model=%s",
                total_latency_ms,
                cache_latency_ms,
                rewrite_latency_ms,
                retrieval_latency_ms,
                generation_latency_ms,
                len(retrieval_outcome.chunks),
                llm_response.model,
            )

            return ConversationalRAGResult(
                query=clean_query,
                selected_query=active_search_query,
                answer=llm_response.content,
                citations=context_result.citations,
                retrieved_chunks=retrieval_outcome.chunks,
                llm_model=llm_response.model,
                embedding_model=self.embedding_provider.model_id,
                provider=llm_response.provider,
                total_latency_ms=total_latency_ms,
                retrieval_latency_ms=retrieval_latency_ms,
                generation_latency_ms=generation_latency_ms,
                rewrite_latency_ms=rewrite_latency_ms,
                cache_latency_ms=cache_latency_ms,
                rewrite_enabled=rewrite_enabled,
                rewrite_accepted=is_accepted,
                rewritten_query=rewritten_text,
                multi_query_enabled=multi_query_enabled or decomposition_enabled,
                generated_queries=generated_queries,
                cache_hit=False,
                token_usage=token_usage,
                retrieval_mode="conversational",
                rag_metadata=rag_meta,
            )
        finally:
            if dedup_token:
                await self.cache.release_dedup_lock(workspace_id, project_id, clean_query, dedup_token)
