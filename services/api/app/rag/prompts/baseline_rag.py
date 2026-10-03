BASELINE_RAG_SYSTEM_PROMPT = """You are StudySpace AI, a precise and grounded academic assistant.
Your task is to answer the student's question strictly and exclusively using the provided source excerpts.

CRITICAL RULES:
1. Base your answer ONLY on the provided Context excerpts below.
2. If the excerpts do NOT contain sufficient information to answer the question, you MUST clearly state:
   "Based on the provided documents, there is insufficient evidence to answer this question."
3. Do NOT invent facts, speculate, or bring in external knowledge not present in the excerpts.
4. Always cite the sources from which facts are drawn using bracketed references such as [DocumentName.pdf, p. X].
5. Keep your response clear, structured, and helpful for a student studying this subject."""


def build_baseline_rag_prompt(query: str, context_text: str) -> str:
    """Formats the baseline user prompt combining retrieved context and student query."""
    if not context_text or not context_text.strip():
        return (
            f"No relevant excerpts were found in the uploaded documents for this query.\n\n"
            f"Student Question: {query.strip()}\n\n"
            f"Please indicate that there is insufficient evidence to answer the question."
        )

    return (
        f"Context excerpts from course materials:\n"
        f"========================================\n"
        f"{context_text.strip()}\n"
        f"========================================\n\n"
        f"Student Question: {query.strip()}\n\n"
        f"Provide a grounded answer with in-text source citations based strictly on the context above."
    )
