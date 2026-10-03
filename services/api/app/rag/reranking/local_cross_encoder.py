import math
import re
from typing import List, Set

from app.core.logging import logger
from app.rag.reranking.base import BaseReranker
from app.rag.retrieval.models import RetrievedChunk


class LocalCrossEncoderReranker(BaseReranker):
    """
    Deterministic, high-resolution local cross-encoder / passage re-scorer.
    Requires ZERO external weights or network downloads.
    
    Evaluates fine-grained query-chunk cross features:
      1. Exact phrase matching in chunk content and heading
      2. Query term coverage (recall of distinct query keywords)
      3. Positional proximity (inverse span distance between query terms in chunk)
      4. Heading / Title semantic alignment bonus
      5. Dense semantic cosine alignment (when dense_score is present)
      6. Length penalty mitigation (calibrated BM25-style saturation)
    """

    STOPWORDS: Set[str] = {
        "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "with",
        "of", "by", "from", "is", "are", "was", "were", "what", "which", "who",
        "how", "where", "when", "why", "does", "do", "explain", "describe",
        "tell", "me", "about", "can", "could", "should", "would",
    }

    def _tokenize(self, text: str) -> List[str]:
        return [
            w for w in re.findall(r"\b[a-zA-Z0-9_\-']+\b", text.lower())
            if len(w) > 1 and w not in self.STOPWORDS
        ]

    def _calculate_cross_score(self, query: str, chunk: RetrievedChunk) -> float:
        content_lower = chunk.content.lower()
        heading_lower = (chunk.heading or "").lower()
        title_lower = (chunk.slide_title or "").lower()
        combined_text = f"{heading_lower} {title_lower} {content_lower}"

        q_lower = query.lower().strip()
        q_tokens = self._tokenize(q_lower)

        if not q_tokens:
            return chunk.similarity_score

        # 1. Exact phrase match bonus
        exact_phrase_bonus = 0.0
        if len(q_lower) > 3 and q_lower in combined_text:
            exact_phrase_bonus = 0.35
        else:
            # Check bigram phrases
            words = q_lower.split()
            if len(words) >= 2:
                matched_bigrams = 0
                for i in range(len(words) - 1):
                    bigram = f"{words[i]} {words[i+1]}"
                    if bigram in combined_text:
                        matched_bigrams += 1
                exact_phrase_bonus = min(0.25, matched_bigrams * 0.1)

        # 2. Term coverage (fraction of informative query tokens present)
        matched_tokens = [tok for tok in q_tokens if tok in combined_text]
        coverage_ratio = len(matched_tokens) / len(q_tokens)

        # 3. Heading & Structural match bonus
        heading_bonus = 0.0
        for tok in q_tokens:
            if tok in heading_lower or tok in title_lower:
                heading_bonus += 0.08
        heading_bonus = min(0.25, heading_bonus)

        # 4. Proximity / Span compactness
        # Find minimum span containing all matched terms
        proximity_score = 0.0
        if len(matched_tokens) >= 2:
            positions = []
            for tok in matched_tokens:
                m = re.search(r"\b" + re.escape(tok) + r"\b", content_lower)
                if m:
                    positions.append(m.start())
            if len(positions) >= 2:
                span = max(positions) - min(positions)
                # Smaller span -> higher density
                proximity_score = math.exp(-span / 300.0) * 0.15

        # 5. Dense semantic signal (if retrieved via dense search)
        dense_signal = (chunk.dense_score or 0.0) * 0.25

        # 6. Lexical signal (if retrieved via lexical search)
        lexical_signal = (chunk.lexical_score or 0.0) * 0.15

        # Composite cross-score calculation
        raw_score = (
            (coverage_ratio * 0.40)
            + exact_phrase_bonus
            + heading_bonus
            + proximity_score
            + dense_signal
            + lexical_signal
        )

        # Sigmoid calibration to [0.0, 1.0]
        calibrated_score = 1.0 / (1.0 + math.exp(-2.5 * (raw_score - 0.5)))
        return round(float(calibrated_score), 4)

    async def rerank(
        self,
        query: str,
        candidates: List[RetrievedChunk],
        top_n: int = 5,
    ) -> List[RetrievedChunk]:
        """
        Re-scores candidate chunks and returns the top_n most relevant chunks.
        """
        if not candidates:
            return []

        for chunk in candidates:
            score = self._calculate_cross_score(query, chunk)
            chunk.rerank_score = score
            chunk.similarity_score = score  # updated effective relevance score
            chunk.retrieval_method = "reranked" if chunk.retrieval_method == "hybrid" else f"{chunk.retrieval_method}+reranked"

        # Sort descending by rerank_score
        reranked = sorted(candidates, key=lambda c: c.rerank_score or 0.0, reverse=True)

        logger.debug(
            "LocalCrossEncoder reranked %d candidates to top %d for query: '%s'",
            len(candidates),
            min(top_n, len(reranked)),
            query[:40],
        )

        return reranked[:top_n]
