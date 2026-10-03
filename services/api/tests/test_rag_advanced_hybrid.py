import uuid
import pytest
from unittest.mock import AsyncMock, patch

from app.rag.context.builder import ContextBuilder
from app.rag.context.models import CitationSource
from app.rag.fusion.rrf import ReciprocalRankFusion
from app.rag.llm.base import LLMResponse
from app.rag.pipeline import AdvancedRAGPipeline
from app.rag.reranking.local_cross_encoder import LocalCrossEncoderReranker
from app.rag.reranking.passthrough import PassthroughReranker
from app.rag.reranking.registry import RerankerModelNotFoundError, get_reranker
from app.rag.retrieval.hybrid_retriever import HybridRetrievalResult, HybridRetriever
from app.rag.retrieval.lexical_retriever import LexicalRetriever
from app.rag.retrieval.models import RetrievedChunk


def make_chunk(
    idx: int,
    content: str,
    heading: str = "Heading",
    sim_score: float = 0.5,
    dense_score: float = 0.5,
    lexical_score: float = 0.5,
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        document_filename="sample_cloud_textbook.pdf",
        workspace_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        chunk_index=idx,
        content=content,
        token_count=len(content.split()),
        page_start=idx,
        page_end=idx,
        slide_number=None,
        slide_title=None,
        section_path=f"Unit {idx}",
        heading=heading,
        similarity_score=sim_score,
        dense_score=dense_score,
        lexical_score=lexical_score,
    )


# -----------------------------------------------------------------------------
# 1. RRF Mathematics & Candidates Tests
# -----------------------------------------------------------------------------
def test_rrf_scoring_and_candidate_merging():
    c1 = make_chunk(1, "Chunk 1 content", sim_score=0.9)
    c2 = make_chunk(2, "Chunk 2 content", sim_score=0.8)
    c3 = make_chunk(3, "Chunk 3 content", sim_score=0.7)
    c4 = make_chunk(4, "Chunk 4 content", sim_score=0.6)

    # Dense: [c1, c2, c3]
    # Lexical: [c3, c2, c4]
    dense_list = [c1, c2, c3]
    lexical_list = [c3, c2, c4]

    fusion = ReciprocalRankFusion(k=60)
    fused = fusion.fuse(dense_candidates=dense_list, lexical_candidates=lexical_list)

    assert len(fused) == 4
    # c3 appeared in both: dense rank 3, lexical rank 1 -> 1/(60+3) + 1/(60+1) = 0.032266
    # c2 appeared in both: dense rank 2, lexical rank 2 -> 1/(60+2) + 1/(60+2) = 0.032258
    assert fused[0].chunk_index == 3
    assert fused[0].retrieval_method == "hybrid"
    assert fused[0].dense_rank == 3
    assert fused[0].lexical_rank == 1

    assert fused[1].chunk_index == 2
    assert fused[1].retrieval_method == "hybrid"

    # c1 only in dense
    assert fused[2].chunk_index == 1
    assert fused[2].retrieval_method == "dense"

    # c4 only in lexical
    assert fused[3].chunk_index == 4
    assert fused[3].retrieval_method == "lexical"


# -----------------------------------------------------------------------------
# 2. Local Cross-Encoder Reranker Tests
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_local_cross_encoder_reranking_accuracy():
    query = "Type 1 hypervisor bare metal virtualization"

    # Chunk A: highly relevant exact terms and heading match
    chunk_a = make_chunk(
        1,
        content="A Type 1 hypervisor runs directly on the bare metal hardware without a host OS. It offers optimal virtualization performance.",
        heading="Type 1 Hypervisors and Bare Metal",
        sim_score=0.5,
    )

    # Chunk B: distantly related
    chunk_b = make_chunk(
        2,
        content="Cloud storage pricing depends on data tiering and replication across availability zones.",
        heading="Cloud Storage Economics",
        sim_score=0.5,
    )

    reranker = LocalCrossEncoderReranker()
    reranked = await reranker.rerank(query=query, candidates=[chunk_b, chunk_a], top_n=2)

    assert len(reranked) == 2
    assert reranked[0].chunk_index == 1
    assert reranked[0].rerank_score > reranked[1].rerank_score
    assert reranked[0].rerank_score > 0.6
    assert reranked[1].rerank_score < 0.6


# -----------------------------------------------------------------------------
# 3. Reranker Registry & Model Availability Guardrails
# -----------------------------------------------------------------------------
def test_reranker_registry_guardrails():
    # 'disabled' gives PassthroughReranker
    p = get_reranker("disabled")
    assert isinstance(p, PassthroughReranker)

    # 'local' gives LocalCrossEncoderReranker
    l = get_reranker("local")
    assert isinstance(l, LocalCrossEncoderReranker)

    # Requesting missing external neural model library raises RerankerModelNotFoundError without downloading
    with pytest.raises(RerankerModelNotFoundError):
        get_reranker("sentence_transformers")


# -----------------------------------------------------------------------------
# 4. Advanced Hybrid Pipeline End-to-End
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_advanced_rag_pipeline_execution():
    ws_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    query = "What is NIST cloud computing?"

    mock_chunk = make_chunk(
        10,
        content="NIST defines cloud computing as a model for enabling ubiquitous network access to shared configurable computing resources.",
        heading="NIST Cloud Definition",
        sim_score=0.85,
    )

    mock_hybrid_retriever = AsyncMock()
    mock_hybrid_retriever.retrieve_detailed.return_value = HybridRetrievalResult(
        chunks=[mock_chunk],
        dense_candidates=[mock_chunk],
        lexical_candidates=[mock_chunk],
        fused_candidates=[mock_chunk],
        dense_latency_ms=120,
        lexical_latency_ms=80,
        fusion_latency_ms=2,
        rerank_latency_ms=5,
        total_latency_ms=130,
    )

    mock_llm = AsyncMock()
    mock_llm.generate.return_value = LLMResponse(
        content="According to NIST, cloud computing enables ubiquitous access to shared resources [sample_cloud_textbook.pdf, p. 10].",
        model="phi4-mini:latest",
        provider="ollama",
        prompt_tokens=90,
        completion_tokens=25,
        latency_ms=650,
    )

    pipeline = AdvancedRAGPipeline(
        retriever=mock_hybrid_retriever,
        llm_provider=mock_llm,
    )

    result = await pipeline.execute(
        query=query,
        workspace_id=ws_id,
        project_id=proj_id,
        dense_top_k=10,
        lexical_top_k=10,
        final_top_k=3,
    )

    assert result.retrieval_mode == "advanced"
    assert "According to NIST" in result.answer
    assert len(result.retrieved_chunks) == 1
    assert result.dense_candidates_count == 1
    assert result.lexical_candidates_count == 1
    assert result.fused_candidates_count == 1
    assert result.dense_latency_ms == 120
    assert result.lexical_latency_ms == 80
    assert result.fusion_latency_ms == 2
    assert result.rerank_latency_ms == 5
