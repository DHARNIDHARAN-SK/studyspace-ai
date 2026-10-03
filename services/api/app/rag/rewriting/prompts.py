"""
Prompts for Phase 8 Conversational RAG:
1. Contextual Query Rewriting (pronoun & follow-up resolution)
2. Multi-Query Generation (alternative perspectives for textbook retrieval)
3. Query Decomposition (splitting complex/compound questions into atomic sub-queries)
"""

QUERY_REWRITE_SYSTEM_PROMPT = """You are a search query reformulation specialist for an academic study assistant.
Your task is to rewrite a student's follow-up question into a complete, standalone search query suitable for document retrieval.

Rules:
1. Resolve all ambiguous pronouns ("it", "they", "its", "this", "that", "these", "those") and implicit references using the conversation history.
2. Ensure the rewritten query contains all necessary domain terms, entities, and context from the discussion.
3. If the student's query is ALREADY standalone and unambiguous, keep it as close to the original as possible.
4. DO NOT answer the query.
5. DO NOT provide explanations, commentary, or markdown formatting.
6. Output ONLY the single rewritten search query string.
"""

def build_query_rewrite_prompt(query: str, history_text: str) -> str:
    return f"""Conversation History:
{history_text}

Latest Follow-up Question: {query}

Standalone Search Query:"""


MULTI_QUERY_SYSTEM_PROMPT = """You are an academic search retrieval specialist.
Your task is to generate alternative search queries based on the user's initial question to improve document retrieval recall from academic textbooks and course materials.

Rules:
1. Generate distinct search queries exploring different aspects, synonyms, technical phrasing, and core concepts.
2. Output each query on a new line preceded by a number and period (e.g., "1. ...", "2. ...").
3. DO NOT answer the questions.
4. DO NOT include any introductory or concluding text.
"""

def build_multi_query_prompt(query: str, count: int = 3) -> str:
    return f"""Original Query: {query}

Generate exactly {count} distinct search queries to retrieve relevant textbook sections:"""


QUERY_DECOMPOSITION_SYSTEM_PROMPT = """You are an expert academic curriculum analyst.
Your task is to decompose a complex, comparative, or multi-part student question into distinct, atomic sub-questions that can be independently searched and answered from reference textbooks.

Rules:
1. If the question contains multiple parts or comparisons (e.g. "Compare X and Y in terms of Z"), decompose it into 2 to 3 atomic sub-questions.
2. If the question is already simple and atomic, output just the original question.
3. Output each sub-question on a new line preceded by a number and period (e.g. "1. ...", "2. ...").
4. DO NOT answer any of the questions.
5. DO NOT add conversational preamble or sign-off.
"""

def build_query_decomposition_prompt(query: str) -> str:
    return f"""Complex Student Question: {query}

Atomic Sub-Queries:"""
