from dataclasses import dataclass, field
import time
from typing import Any, Dict, List, Optional
import uuid

from app.core.config import settings
from app.core.logging import logger
from app.rag.context.builder import ContextBuilder
from app.rag.context.models import CitationSource
from app.rag.embeddings.base import BaseEmbeddingProvider
from app.rag.embeddings.registry import get_embedding_provider
from app.rag.llm.base import BaseLLMProvider
from app.rag.llm.registry import get_llm_provider
from app.rag.prompts.baseline_rag import (
    BASELINE_RAG_SYSTEM_PROMPT,
    build_baseline_rag_prompt,
)
from app.rag.retrieval.hybrid_retriever import HybridRetrievalResult, HybridRetriever
from app.rag.retrieval.models import RetrievedChunk
from app.rag.retrieval.vector_retriever import VectorRetriever


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
