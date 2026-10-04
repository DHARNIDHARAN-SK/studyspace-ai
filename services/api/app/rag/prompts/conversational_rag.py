"""
Prompts for Phase 8 Conversational RAG Generation.
Combines bounded conversational history with retrieved document context excerpts.
"""
from typing import Optional

CONVERSATIONAL_RAG_SYSTEM_PROMPT = """You are StudySpace AI, an advanced, grounded conversational academic study assistant.
Your task is to answer the student's question accurately, clearly, and helpfully using the provided document excerpts.

CRITICAL RULES:
1. Base all factual claims strictly and exclusively on the provided Document Context excerpts below.
2. The Conversation History is provided ONLY for conversational flow and context (e.g., resolving references and maintaining discussion coherence). DO NOT use conversation history as a substitute for factual document evidence.
3. If the document context excerpts do NOT contain sufficient information to answer the question, state:
   "Based on the provided documents, there is insufficient evidence to answer this question."
4. Do NOT invent facts, hallucinate, or extrapolate beyond the provided document context.
5. Provide specific in-text source citations referencing the exact document filename and page from the context headers, e.g. [exact_filename, p. X] or [exact_filename, Slide X]. NEVER output literal placeholders such as "[Document.pdf]" or "[DocumentName.pdf]" — strictly cite using the real document filename from the context header.
6. Maintain an encouraging, academic tone suitable for university-level coursework.
"""

def build_conversational_rag_prompt(
    query: str,
    context_text: str,
    history_text: Optional[str] = None,
) -> str:
    """
    Constructs the prompt for conversational RAG generation.
    """
    sections = []

    if history_text and history_text.strip():
        sections.append(f"Recent Discussion:\n{history_text.strip()}\n")

    if not context_text or not context_text.strip():
        sections.append(
            "Document Context:\nNo relevant excerpts were found in the uploaded documents for this query.\n"
        )
    else:
        sections.append(
            f"Document Context Excerpts:\n"
            f"========================================\n"
            f"{context_text.strip()}\n"
            f"========================================\n"
        )

    sections.append(
        f"Student Question: {query.strip()}\n\n"
        f"Provide a grounded, comprehensive answer with specific citations based strictly on the document context."
    )

    return "\n".join(sections)
