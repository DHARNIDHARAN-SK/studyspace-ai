import uuid
import pytest
from unittest.mock import AsyncMock, patch

from app.rag.context.builder import ContextBuilder
from app.rag.llm.ollama_provider import OllamaLLMProvider
from app.rag.prompts.baseline_rag import BASELINE_RAG_SYSTEM_PROMPT, build_baseline_rag_prompt
from app.rag.retrieval.models import RetrievedChunk


def test_context_builder_and_citation_mapping():
    builder = ContextBuilder(max_context_chars=1000)

    doc_id = uuid.uuid4()
    ws_id = uuid.uuid4()
    proj_id = uuid.uuid4()

    chunks = [
        RetrievedChunk(
            chunk_id=uuid.uuid4(),
            document_id=doc_id,
            document_filename="Chapter1.pdf",
            workspace_id=ws_id,
            project_id=proj_id,
            chunk_index=0,
            content="Cloud computing provides on-demand network access to shared computing resources.",
            token_count=15,
            page_start=4,
            page_end=4,
            slide_number=None,
            slide_title=None,
            section_path="1.1 Overview",
            heading=None,
            similarity_score=0.92,
        ),
        RetrievedChunk(
            chunk_id=uuid.uuid4(),
            document_id=doc_id,
            document_filename="Chapter1.pdf",
            workspace_id=ws_id,
            project_id=proj_id,
            chunk_index=1,
            # Duplicate text should be filtered out
            content="Cloud computing provides on-demand network access to shared computing resources.",
            token_count=15,
            page_start=4,
            page_end=4,
            slide_number=None,
            slide_title=None,
            section_path="1.1 Overview",
            heading=None,
            similarity_score=0.92,
        ),
        RetrievedChunk(
            chunk_id=uuid.uuid4(),
            document_id=doc_id,
            document_filename="Chapter1.pdf",
            workspace_id=ws_id,
            project_id=proj_id,
            chunk_index=2,
            content="Key deployment models include private, public, community, and hybrid clouds.",
            token_count=14,
            page_start=9,
            page_end=10,
            slide_number=None,
            slide_title=None,
            section_path="1.3 Deployment Models",
            heading=None,
            similarity_score=0.88,
        ),
    ]

    res = builder.build_context(chunks)

    # Duplicate was filtered: exactly 2 distinct blocks and citations
    assert len(res.citations) == 2
    assert "Chapter1.pdf" in res.context_text
    assert "1.1 Overview" in res.context_text

    # Citation 1
    cit1 = res.citations[0]
    assert cit1.page_start == 4
    assert cit1.citation_label == "[Chapter1.pdf, p. 4]"
    assert cit1.similarity_score == 0.92

    # Citation 2
    cit2 = res.citations[1]
    assert cit2.page_start == 9
    assert cit2.page_end == 10
    assert cit2.citation_label == "[Chapter1.pdf, pp. 9-10]"


def test_baseline_prompt_grounding_and_insufficient_evidence():
    # Test with valid context
    prompt = build_baseline_rag_prompt(
        query="What are the cloud deployment models?",
        context_text="Private, public, and hybrid clouds.",
    )
    assert "Private, public, and hybrid clouds." in prompt
    assert "What are the cloud deployment models?" in prompt
    assert "insufficient evidence" in BASELINE_RAG_SYSTEM_PROMPT.lower()

    # Test with empty context (insufficient evidence signal)
    empty_prompt = build_baseline_rag_prompt(
        query="What is quantum entanglement?",
        context_text="",
    )
    assert "insufficient evidence" in empty_prompt.lower()


@pytest.mark.asyncio
async def test_ollama_llm_provider_generation():
    provider = OllamaLLMProvider(model_id="phi4-mini:latest")

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = lambda: None
        mock_resp.json = lambda: {
            "response": "Cloud computing is on-demand delivery of IT resources [Chapter1.pdf, p. 4].",
            "prompt_eval_count": 85,
            "eval_count": 22,
        }
        mock_post.return_value = mock_resp

        res = await provider.generate(
            prompt="What is cloud computing?",
            system_prompt=BASELINE_RAG_SYSTEM_PROMPT,
        )

        assert "on-demand delivery" in res.content
        assert res.model == "phi4-mini:latest"
        assert res.provider == "ollama"
        assert res.prompt_tokens == 85
        assert res.completion_tokens == 22
        assert res.latency_ms >= 0
