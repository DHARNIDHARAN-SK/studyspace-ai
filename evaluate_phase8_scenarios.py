import asyncio
import json
import time
import uuid
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.db.session import get_session_factory
from app.rag.pipeline import ConversationalRAGPipeline
from app.services.chat_service import ChatService


WS_ID = uuid.UUID("6869b194-56b0-47c9-bb2c-2d373e02706e")
PROJ_ID = uuid.UUID("a0583e36-c065-43eb-a020-35fb160f5580")
USER_ID = uuid.UUID("23e5f4e6-35f2-4992-ae23-1f7db4ea61de")


async def run_scenario(
    chat_service: ChatService,
    title: str,
    query: str,
    conv_id: Optional[uuid.UUID] = None,
    rewrite_enabled: bool = True,
    selected_query: str = None,
    rewrite_accepted: bool = None,
    multi_query_enabled: bool = False,
    decomposition_enabled: bool = False,
) -> Dict[str, Any]:
    print(f"\n========================================================")
    print(f"Running Scenario: {title}")
    print(f"Query: '{query}' (Conv ID: {conv_id})")
    print(f"Settings: rewrite={rewrite_enabled}, mq={multi_query_enabled}, decomp={decomposition_enabled}, selected='{selected_query}'")

    res = await chat_service.handle_chat_query(
        workspace_id=WS_ID,
        project_id=PROJ_ID,
        user_id=USER_ID,
        query=query,
        conversation_id=conv_id,
        retrieval_mode="conversational",
        rewrite_enabled=rewrite_enabled,
        selected_query=selected_query,
        rewrite_accepted=rewrite_accepted,
        multi_query_enabled=multi_query_enabled,
        decomposition_enabled=decomposition_enabled,
        top_k=5,
    )

    actual_conv_id = uuid.UUID(res["conversation_id"])
    metrics = res["metrics"]
    msg = res["message"]
    print(f"Outcome: total={metrics.get('total_latency_ms')}ms, cache_hit={metrics.get('cache_hit')}, rewrite_lat={metrics.get('rewrite_latency_ms')}ms")
    print(f"Selected Query: '{metrics.get('selected_query')}'")
    print(f"Rewritten Query: '{metrics.get('rewritten_query')}'")
    print(f"Generated Queries: {metrics.get('generated_queries')}")
    print(f"Citations ({len(msg['citations'])}): {[c['citation_label'] for c in msg['citations']]}")
    print(f"Answer snippet: {msg['content'][:180]}...")

    return {
        "title": title,
        "input_query": query,
        "conversation_id": str(actual_conv_id),
        "selected_query": metrics.get("selected_query"),
        "rewritten_query": metrics.get("rewritten_query"),
        "rewrite_enabled": metrics.get("rewrite_enabled"),
        "rewrite_accepted": metrics.get("rewrite_accepted"),
        "multi_query_enabled": metrics.get("multi_query_enabled"),
        "generated_queries": metrics.get("generated_queries", []),
        "cache_hit": metrics.get("cache_hit", False),
        "cached_query": metrics.get("cached_query"),
        "total_latency_ms": metrics.get("total_latency_ms"),
        "retrieval_latency_ms": metrics.get("retrieval_latency_ms"),
        "generation_latency_ms": metrics.get("generation_latency_ms"),
        "rewrite_latency_ms": metrics.get("rewrite_latency_ms", 0),
        "cache_latency_ms": metrics.get("cache_latency_ms", 0),
        "retrieved_chunks_count": metrics.get("retrieved_chunks"),
        "dense_candidates": metrics.get("dense_candidates", 0),
        "lexical_candidates": metrics.get("lexical_candidates", 0),
        "fused_candidates": metrics.get("fused_candidates", 0),
        "answer": msg["content"],
        "citations": msg["citations"],
    }, actual_conv_id


async def main():
    chat_service = ChatService()

    # Scenario 1: First question
    s1, conv_1 = await run_scenario(
        chat_service=chat_service,
        title="Scenario 1: First Question (Standalone Topic Introduction)",
        query="What are the key cloud service models?",
        conv_id=None,
        rewrite_enabled=True,
    )

    # Scenario 2: Follow-up pronoun resolution (using same conversation conv_1)
    s2, _ = await run_scenario(
        chat_service=chat_service,
        title="Scenario 2: Follow-up Pronoun Resolution (Contextual Continuity)",
        query="What are their main differences and trade-offs?",
        conv_id=conv_1,
        rewrite_enabled=True,
    )

    # Scenario 3: Complex question decomposition
    s3, conv_3 = await run_scenario(
        chat_service=chat_service,
        title="Scenario 3: Complex Question Decomposition (Comparative Analysis)",
        query="Compare public and private clouds in terms of security and scalability",
        conv_id=None,
        decomposition_enabled=True,
    )

    # Scenario 4: Multi-query retrieval
    s4, conv_4 = await run_scenario(
        chat_service=chat_service,
        title="Scenario 4: Multi-Query Parallel Hybrid Retrieval",
        query="Explain virtualization and hypervisors in cloud computing",
        conv_id=None,
        multi_query_enabled=True,
    )

    # Scenario 5: Semantic Cache Hit & Miss
    # 5A: Miss (initial populate)
    s5a, conv_5 = await run_scenario(
        chat_service=chat_service,
        title="Scenario 5A: Semantic Cache Miss (Initial Computation)",
        query="What is cloud elasticity and scalability?",
        conv_id=None,
        rewrite_enabled=False,
    )

    # 5B: Hit (semantically equivalent query)
    s5b, _ = await run_scenario(
        chat_service=chat_service,
        title="Scenario 5B: Semantic Cache Hit (Sub-10ms Instant Retrieval)",
        query="What is cloud elasticity and scalability?",
        conv_id=conv_5,
        rewrite_enabled=False,
    )

    # Scenario 6: User control over rewritten queries
    # Populate history first
    _, conv_6a = await run_scenario(
        chat_service=chat_service,
        title="Scenario 6 Pre-turn: Context Setup",
        query="Explain cloud storage architecture and security",
        conv_id=None,
        rewrite_enabled=False,
    )

    # Preview rewrite
    preview = await chat_service.preview_rewrite(
        workspace_id=WS_ID,
        project_id=PROJ_ID,
        user_id=USER_ID,
        query="What are its main risks?",
        conversation_id=conv_6a,
    )
    print("\nPreview Rewrite Result:", json.dumps(preview, indent=2))

    # 6A: User accepts rewritten query
    s6a, _ = await run_scenario(
        chat_service=chat_service,
        title="Scenario 6A: User Accepts Proposed Rewritten Query",
        query="What are its main risks?",
        conv_id=conv_6a,
        rewrite_enabled=True,
        selected_query=preview["rewritten_query"],
        rewrite_accepted=True,
    )

    # 6B: User rejects rewrite, forces original query
    _, conv_6b = await run_scenario(
        chat_service=chat_service,
        title="Scenario 6B Pre-turn: Context Setup",
        query="Explain cloud storage architecture and security",
        conv_id=None,
        rewrite_enabled=False,
    )
    s6b, _ = await run_scenario(
        chat_service=chat_service,
        title="Scenario 6B: User Rejects Rewrite (Keeps Raw Query)",
        query="What are its main risks?",
        conv_id=conv_6b,
        rewrite_enabled=False,
        selected_query="What are its main risks?",
        rewrite_accepted=False,
    )

    results = {
        "timestamp": time.time(),
        "scenarios": [s1, s2, s3, s4, s5a, s5b, s6a, s6b],
        "preview": preview,
    }

    with open("phase8_evaluation_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\n\nAll 6 scenarios completed successfully! Results written to phase8_evaluation_results.json")

if __name__ == "__main__":
    asyncio.run(main())
