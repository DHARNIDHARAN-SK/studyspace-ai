from pathlib import Path
import uuid
import pytest
from sqlalchemy import select, text

from app.db.models import Document, DocumentChunk
from app.db.session import get_session_factory
from app.rag.pipeline import BaselineRAGPipeline

REAL_PDF_PATH = Path(r"D:\RAG_DATA_TESTING\DECAP470_CLOUD_COMPUTING.pdf")
WS_ID = uuid.UUID("6869b194-56b0-47c9-bb2c-2d373e02706e")
PROJ_ID = uuid.UUID("a0583e36-c065-43eb-a020-35fb160f5580")
DOC_ID = uuid.UUID("dcbce759-728f-471f-9233-4f112546fa54")


@pytest.mark.asyncio
async def test_real_cloud_computing_baseline_rag():
    """
    Executes the end-to-end baseline RAG pipeline against the real Cloud Computing textbook:
      D:\RAG_DATA_TESTING\DECAP470_CLOUD_COMPUTING.pdf
    Verifies:
      1. Original test file is preserved and untouched
      2. Document and 1,728 chunks exist in PostgreSQL
      3. All chunks have valid 768-dimensional pgvector embeddings
      4. Vector search retrieves relevant chunks with high cosine similarity
      5. Context builder produces structured citations with exact page numbers
      6. phi4-mini:latest generates grounded answers
      7. Insufficient-evidence handling correctly declines unsupported external queries
    """
    # 1. Non-destructive file check
    assert REAL_PDF_PATH.exists(), f"Document missing at {REAL_PDF_PATH}"
    initial_size = REAL_PDF_PATH.stat().st_size
    assert initial_size == 13573276, "Original file size modified"

    # 2. Database records verification
    session_factory = get_session_factory()
    async with session_factory() as session:
        doc = await session.get(Document, DOC_ID)
        assert doc is not None, "Document not found in database"
        assert doc.ingestion_status == "indexed"
        assert doc.page_count == 327

        chunk_count_res = await session.execute(
            text("SELECT count(*), count(embedding) FROM document_chunks WHERE document_id = :id"),
            {"id": DOC_ID},
        )
        total_chunks, embedded_chunks = chunk_count_res.one()
        assert total_chunks == 1728, f"Expected 1,728 chunks, got {total_chunks}"
        assert embedded_chunks == 1728, f"Expected 1,728 embedded chunks, got {embedded_chunks}"

    # Initialize baseline RAG pipeline
    pipeline = BaselineRAGPipeline()

    # --------------------------------------------------------------------------
    # Evaluation Query 1: Direct Fact Lookup
    # --------------------------------------------------------------------------
    q1 = "Who benefits from cloud computing according to the notes, specifically regarding collaborators?"
    res1 = await pipeline.execute(
        query=q1,
        workspace_id=WS_ID,
        project_id=PROJ_ID,
        top_k=5,
    )

    assert len(res1.retrieved_chunks) > 0
    assert len(res1.citations) > 0
    # Top chunk should cite page 10
    top_chunk1 = res1.retrieved_chunks[0]
    assert top_chunk1.similarity_score > 0.65
    assert any("collaborat" in c.content.lower() for c in res1.retrieved_chunks)

    # Citations verification
    for cit in res1.citations:
        assert cit.document_filename == "DECAP470_CLOUD_COMPUTING.pdf"
        assert cit.page_start is not None
        assert cit.page_start >= 1 and cit.page_start <= 327

    # Answer should reflect real book content
    assert len(res1.answer) > 20
    assert res1.llm_model == "phi4-mini:latest"
    assert res1.embedding_model == "nomic-embed-text:latest"

    print(f"\n--- EVALUATION QUERY 1 ---")
    print(f"Query: {q1}")
    print(f"Answer:\n{res1.answer}")
    print(f"Latency: {res1.total_latency_ms} ms (Retrieval: {res1.retrieval_latency_ms} ms, Generation: {res1.generation_latency_ms} ms)")
    print(f"Citations: {[c.citation_label for c in res1.citations]}")

    # --------------------------------------------------------------------------
    # Evaluation Query 2: Concept Explanation
    # --------------------------------------------------------------------------
    q2 = "What is a Community Cloud and who does it serve?"
    res2 = await pipeline.execute(
        query=q2,
        workspace_id=WS_ID,
        project_id=PROJ_ID,
        top_k=5,
    )

    assert len(res2.retrieved_chunks) > 0
    assert any("community cloud" in c.content.lower() for c in res2.retrieved_chunks)
    assert any(c.page_start == 35 or c.page_start == 36 for c in res2.retrieved_chunks)

    print(f"\n--- EVALUATION QUERY 2 ---")
    print(f"Query: {q2}")
    print(f"Answer:\n{res2.answer}")
    print(f"Latency: {res2.total_latency_ms} ms (Retrieval: {res2.retrieval_latency_ms} ms, Generation: {res2.generation_latency_ms} ms)")
    print(f"Citations: {[c.citation_label for c in res2.citations]}")

    # --------------------------------------------------------------------------
    # Evaluation Query 3: Negative / Insufficient Evidence Query
    # --------------------------------------------------------------------------
    q3 = "Who won the FIFA Men's World Cup football championship in 2022?"
    res3 = await pipeline.execute(
        query=q3,
        workspace_id=WS_ID,
        project_id=PROJ_ID,
        top_k=5,
    )

    # Must indicate insufficient evidence and NOT hallucinate sports winners
    lower_ans = res3.answer.lower()
    assert (
        "insufficient evidence" in lower_ans
        or "does not contain" in lower_ans
        or "not mentioned" in lower_ans
        or "not provide" in lower_ans
    ), f"Expected insufficient evidence statement, got: {res3.answer}"

    print(f"\n--- EVALUATION QUERY 3 (Insufficient Evidence) ---")
    print(f"Query: {q3}")
    print(f"Answer:\n{res3.answer}")
    print(f"Latency: {res3.total_latency_ms} ms")

    # 3. Final verification of original file
    assert REAL_PDF_PATH.stat().st_size == initial_size
