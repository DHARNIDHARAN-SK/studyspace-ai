from dataclasses import dataclass, field
import re
import time
from typing import List, Optional

from app.core.config import settings
from app.core.logging import logger
from app.rag.conversation.context_manager import (
    ConversationContextManager,
    ConversationTurn,
)
from app.rag.llm.base import BaseLLMProvider
from app.rag.llm.registry import get_llm_provider
from app.rag.rewriting.prompts import (
    QUERY_DECOMPOSITION_SYSTEM_PROMPT,
    QUERY_REWRITE_SYSTEM_PROMPT,
    MULTI_QUERY_SYSTEM_PROMPT,
    build_multi_query_prompt,
    build_query_decomposition_prompt,
    build_query_rewrite_prompt,
)


@dataclass
class RewrittenQueryResult:
    original_query: str
    rewritten_query: str
    was_rewritten: bool
    latency_ms: int = 0
    reason: Optional[str] = None


class QueryTransformationService:
    """
    Transforms queries for Phase 8 Conversational RAG:
    - Contextual rewrite (resolves pronouns & conversation context)
    - Multi-query expansion (generates varied retrieval angles)
    - Query decomposition (breaks complex questions into atomic sub-queries)
    """

    def __init__(self, llm_provider: Optional[BaseLLMProvider] = None):
        self.llm_provider = llm_provider or get_llm_provider()

    async def rewrite_query(
        self,
        query: str,
        history: List[ConversationTurn],
    ) -> RewrittenQueryResult:
        """
        Rewrites a query in light of previous conversation turns to make it standalone.
        If history is empty or rewriting produces an invalid result, falls back to original query.
        """
        clean_query = query.strip()
        if not history:
            return RewrittenQueryResult(
                original_query=clean_query,
                rewritten_query=clean_query,
                was_rewritten=False,
                latency_ms=0,
                reason="No conversation history to resolve.",
            )

        history_text = ConversationContextManager.format_history_for_rewrite(history)
        prompt = build_query_rewrite_prompt(clean_query, history_text)

        start_time = time.time()
        try:
            response = await self.llm_provider.generate(
                prompt=prompt,
                system_prompt=QUERY_REWRITE_SYSTEM_PROMPT,
                temperature=0.0,
                max_tokens=100,
            )
            latency_ms = int((time.time() - start_time) * 1000)

            raw_rewritten = response.content.strip()
            # Clean common artifacts (e.g., quotes, 'Standalone Search Query:' prefixes, markdown)
            cleaned = self._clean_single_query(raw_rewritten)

            if not cleaned or len(cleaned) < 3:
                return RewrittenQueryResult(
                    original_query=clean_query,
                    rewritten_query=clean_query,
                    was_rewritten=False,
                    latency_ms=latency_ms,
                    reason="Rewriter produced empty or degenerate output.",
                )

            is_different = cleaned.lower() != clean_query.lower()
            return RewrittenQueryResult(
                original_query=clean_query,
                rewritten_query=cleaned,
                was_rewritten=is_different,
                latency_ms=latency_ms,
                reason="Contextual rewrite successfully generated." if is_different else "Query already standalone.",
            )
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.warning("Query rewrite failed, falling back to original query: %s", e)
            return RewrittenQueryResult(
                original_query=clean_query,
                rewritten_query=clean_query,
                was_rewritten=False,
                latency_ms=latency_ms,
                reason=f"Rewriter error: {str(e)}",
            )

    async def generate_multi_queries(
        self,
        query: str,
        count: int = settings.RAG_MULTI_QUERY_COUNT,
    ) -> List[str]:
        """
        Generates alternative search queries to improve retrieval recall.
        Always guarantees at least the original query in the return list.
        """
        clean_query = query.strip()
        if count <= 1:
            return [clean_query]

        prompt = build_multi_query_prompt(clean_query, count=count)
        try:
            response = await self.llm_provider.generate(
                prompt=prompt,
                system_prompt=MULTI_QUERY_SYSTEM_PROMPT,
                temperature=0.3,
                max_tokens=150,
            )
            queries = self._parse_numbered_list(response.content)
            
            # Ensure the primary query is included
            unified = [clean_query]
            for q in queries:
                q_clean = self._clean_single_query(q)
                if q_clean and q_clean.lower() != clean_query.lower() and q_clean not in unified:
                    unified.append(q_clean)
                if len(unified) >= count + 1:
                    break

            return unified
        except Exception as e:
            logger.warning("Multi-query generation failed, falling back to original: %s", e)
            return [clean_query]

    async def decompose_query(
        self,
        query: str,
    ) -> List[str]:
        """
        Decomposes complex multi-part questions into atomic sub-queries.
        """
        clean_query = query.strip()
        prompt = build_query_decomposition_prompt(clean_query)
        try:
            response = await self.llm_provider.generate(
                prompt=prompt,
                system_prompt=QUERY_DECOMPOSITION_SYSTEM_PROMPT,
                temperature=0.0,
                max_tokens=150,
            )
            sub_queries = self._parse_numbered_list(response.content)
            cleaned_subs = [self._clean_single_query(sq) for sq in sub_queries if self._clean_single_query(sq)]
            
            if not cleaned_subs:
                return [clean_query]

            return cleaned_subs
        except Exception as e:
            logger.warning("Query decomposition failed, falling back to original: %s", e)
            return [clean_query]

    @staticmethod
    def _clean_single_query(raw_text: str) -> str:
        text = raw_text.strip()
        # Remove markdown bold/italics
        text = text.replace("**", "").replace("*", "")
        # Remove typical prefixes
        text = re.sub(r'^(Standalone Search Query|Rewritten Query|Search Query|Query):\s*', '', text, flags=re.IGNORECASE)
        # Take first line if multiple lines returned
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if lines:
            text = lines[0]
        # Remove surrounding quotes
        text = text.strip('"\'`')
        return text.strip()

    @staticmethod
    def _parse_numbered_list(raw_text: str) -> List[str]:
        items = []
        for line in raw_text.splitlines():
            line = line.strip()
            if not line:
                continue
            # Match "1. ", "1) ", "- ", "* "
            cleaned = re.sub(r'^(\d+[\.\)]|\-|\*)\s*', '', line).strip()
            if cleaned:
                items.append(cleaned)
        return items
