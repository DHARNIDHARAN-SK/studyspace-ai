import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock

from app.rag.evaluation.dataset import get_evaluation_dataset
from app.rag.evaluation.evaluator import RAGEvaluator
from app.rag.evaluation.metrics import (
    calculate_answer_relevance,
    calculate_context_precision,
    calculate_context_recall,
    calculate_faithfulness,
    calculate_mrr,
    calculate_ndcg,
    calculate_percentile,
    calculate_recall_at_k,
)
from app.rag.evaluation.models import EvaluationItem
from app.rag.retrieval.models import RetrievedChunk


def _make_dummy_chunk(page: int, content: str, score: float = 0.8) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        document_filename="DECAP470_CLOUD_COMPUTING.pdf",
        workspace_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        chunk_index=0,
        content=content,
        token_count=100,
        page_start=page,
        page_end=page,
        slide_number=None,
        slide_title=None,
        section_path=None,
        heading=None,
        similarity_score=score,
        retrieval_method="dense",
    )


def test_recall_at_k():
    chunk1 = _make_dummy_chunk(10, "Collaborators share documents in real-time.")
    chunk2 = _make_dummy_chunk(45, "Something unrelated to cloud computing.")
    chunks = [chunk1, chunk2]

    # Ground truth on page 10
    recall = calculate_recall_at_k(chunks, 10, 11, ["collaborators", "documents"], k=5)
    assert recall >= 0.8

    # Unrelated pages and keywords
    recall_zero = calculate_recall_at_k(chunks, 90, 95, ["quantum", "cryptography"], k=5)
    assert recall_zero == 0.0


def test_mrr_calculation():
    chunk1 = _make_dummy_chunk(45, "Irrelevant content.")
    chunk2 = _make_dummy_chunk(10, "Relevant collaborators notes.")
    chunks = [chunk1, chunk2]

    mrr = calculate_mrr(chunks, 10, 11, ["collaborators"])
    # 2nd chunk is relevant -> 1/2 = 0.5
    assert mrr == 0.5


def test_ndcg_calculation():
    chunk1 = _make_dummy_chunk(10, "Direct hit on page 10.")
    chunk2 = _make_dummy_chunk(20, "Secondary mention.")
    chunks = [chunk1, chunk2]

    ndcg = calculate_ndcg(chunks, 10, 10, ["direct"], k=5)
    assert ndcg == 1.0


def test_context_precision_and_recall():
    chunk1 = _make_dummy_chunk(10, "NIST cloud definition includes on-demand self-service.")
    chunk2 = _make_dummy_chunk(50, "Unrelated material.")
    chunks = [chunk1, chunk2]

    precision = calculate_context_precision(chunks, 10, 10, ["NIST", "on-demand"])
    assert precision == 0.5

    recall = calculate_context_recall(
        retrieved_context=chunk1.content,
        ground_truth_answer="NIST specifies on-demand self-service and resource pooling.",
        ground_truth_keywords=["NIST", "on-demand", "pooling"],
    )
    # NIST and on-demand are in context -> 2/3 = 0.6667
    assert 0.6 <= recall <= 0.7


def test_faithfulness_and_relevance():
    context = "Cloud computing provides on-demand self-service and rapid elasticity."
    faithful_answer = "Cloud computing offers rapid elasticity and on-demand self-service."
    unfaithful_answer = "Cloud computing was invented by aliens on Mars in 1842."

    faith_high = calculate_faithfulness(faithful_answer, context)
    assert faith_high >= 0.8

    faith_low = calculate_faithfulness(unfaithful_answer, context)
    assert faith_low <= 0.2

    # Insufficient evidence statement should be 1.0 faithful
    assert calculate_faithfulness("There is insufficient evidence in the document.", "") == 1.0

    # Relevance
    rel = calculate_answer_relevance(
        answer="PaaS benefits include developer productivity and automated deployment.",
        query="What are PaaS benefits?",
        ground_truth_answer="Developer productivity and deployment automation are main benefits.",
    )
    assert rel >= 0.5


def test_percentile_calculation():
    vals = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    p50 = calculate_percentile(vals, 50.0)
    p95 = calculate_percentile(vals, 95.0)
    assert 50.0 <= p50 <= 60.0
    assert 90.0 <= p95 <= 100.0


def test_dataset_completeness():
    dataset = get_evaluation_dataset()
    assert len(dataset) == 8
    categories = {it.category for it in dataset}
    assert "fact_lookup" in categories
    assert "concept_explanation" in categories
    assert "comparative_analysis" in categories
    assert "conversational_followup" in categories

    for it in dataset:
        assert it.id.startswith("EVAL-")
        assert len(it.query) > 10
        assert len(it.ground_truth_keywords) >= 3
        assert it.relevant_page_start > 0


@pytest.mark.asyncio
async def test_evaluator_scoring_flow():
    ws_id = uuid.uuid4()
    proj_id = uuid.uuid4()

    item = EvaluationItem(
        id="TEST-01",
        category="fact_lookup",
        query="Test query?",
        ground_truth_answer="Test ground truth answer.",
        relevant_page_start=10,
        relevant_page_end=11,
        ground_truth_keywords=["test", "query"],
        ground_truth_section="Test Section",
    )

    evaluator = RAGEvaluator(workspace_id=ws_id, project_id=proj_id, dataset=[item])

    # Mock baseline pipeline response
    mock_chunk = _make_dummy_chunk(10, "Test query content here.")
    mock_res = MagicMock()
    mock_res.answer = "Test query generated answer."
    mock_res.retrieved_chunks = [mock_chunk]
    mock_res.total_latency_ms = 120
    mock_res.retrieval_latency_ms = 40
    mock_res.generation_latency_ms = 80
    mock_res.token_usage = {"prompt_tokens": 100, "completion_tokens": 20}

    evaluator.baseline_pipeline.execute = AsyncMock(return_value=mock_res)

    result = await evaluator.evaluate_item_baseline(item)
    assert result.item_id == "TEST-01"
    assert result.recall_at_k >= 0.5
    assert result.mrr == 1.0
    assert result.total_latency_ms == 120
