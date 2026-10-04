import re
from typing import Optional, Tuple
from pydantic import BaseModel


class IntentClassificationResult(BaseModel):
    intent: str  # "casual", "study", "mixed"
    extracted_study_query: Optional[str] = None
    casual_greeting: Optional[str] = None
    reason: str


# Common casual phrases and patterns
CASUAL_EXACT_PATTERNS = {
    "hi",
    "hello",
    "hey",
    "hey there",
    "good morning",
    "good afternoon",
    "good evening",
    "how are you",
    "how are you doing",
    "how are you today",
    "how are you doing today",
    "hello how are you",
    "hello how are you doing",
    "hello how are you doing today",
    "hi how are you",
    "hi how are you doing",
    "hi how are you doing today",
    "hey how are you",
    "hey how are you doing",
    "hey how are you doing today",
    "how's it going",
    "what are you doing",
    "what's up",
    "whats up",
    "sup",
    "i'm tired",
    "im tired",
    "i am tired",
    "i'm sleepy",
    "i feel tired",
    "thanks",
    "thank you",
    "thank you so much",
    "thx",
    "thanks a lot",
    "okay",
    "ok",
    "cool",
    "got it",
    "great",
    "awesome",
    "nice",
    "bye",
    "goodbye",
    "see you",
    "can you help me study",
    "can you help me study?",
    "help me study",
    "i want to study",
    "ready to study",
}

GREETING_PREFIX_REGEX = re.compile(
    r"^(?:(?:hi|hello|hey|hey there|good morning|good afternoon|good evening)[,!.\s]*)+(?:hope you(?:'re| are) doing well[,!.\s]*)?(?:how are you(?: doing)?(?:\s+today)?[,!.\s]*)?",
    re.IGNORECASE,
)

STUDY_INTENT_KEYWORDS = [
    "what is",
    "what are",
    "explain",
    "describe",
    "compare",
    "difference between",
    "summarize",
    "summary",
    "definition",
    "define",
    "according to",
    "pdf",
    "document",
    "notes",
    "material",
    "chapter",
    "section",
    "syllabus",
    "lecture",
    "citation",
    "citations",
    "advantages",
    "benefits",
    "disadvantages",
    "drawbacks",
    "characteristics",
    "types of",
    "how does",
    "why does",
    "its benefits",
    "its advantages",
    "its features",
]


def classify_conversation_intent(query: str) -> IntentClassificationResult:
    """
    Distinguishes casual conversation from document/study queries BEFORE retrieval.
    Enforces strict RAG separation: casual conversations NEVER trigger vector search,
    lexical search, or citations.
    """
    cleaned = query.strip()
    lower = cleaned.lower()
    # Remove trailing punctuation for normalized matching
    normalized = re.sub(r"[?!.,]+$", "", lower).strip()

    # 1. Exact casual phrases
    if normalized in CASUAL_EXACT_PATTERNS:
        return IntentClassificationResult(
            intent="casual",
            reason=f"Matched exact casual pattern: '{normalized}'",
        )

    # 2. General statements of intention to study without a specific document query
    # e.g., "I'm going to study today.", "I'm going to study Cloud Computing today."
    study_intent_decl = re.match(
        r"^(i'?m going to study|i am going to study|let'?s study|today i will study|i want to learn about)\s+([^.?!]+)?",
        lower,
    )
    if study_intent_decl and not any(kw in lower for kw in ["what", "explain", "why", "how", "according to", "pdf"]):
        subject = study_intent_decl.group(2)
        if subject:
            subject = subject.replace("today", "").strip()
        return IntentClassificationResult(
            intent="casual",
            casual_greeting=subject,
            reason="Casual study readiness declaration without specific question",
        )

    # 3. Check for mixed intent (greeting prefix + actual study query)
    prefix_match = GREETING_PREFIX_REGEX.match(cleaned)
    if prefix_match:
        remainder = cleaned[prefix_match.end():].strip()
        clean_rem = re.sub(r"[?!.,]+$", "", remainder.lower()).strip()
        is_casual_word = clean_rem in {"", "today", "there", "friend", "bot", "assistant", "studyspace"}
        # If remainder is substantial and asks a study query
        if not is_casual_word and len(clean_rem) > 3 and (
            any(kw in remainder.lower() for kw in STUDY_INTENT_KEYWORDS)
            or (len(clean_rem.split()) >= 3 and any(w in clean_rem for w in ["what", "how", "why", "when", "where", "can you", "tell me", "explain", "describe", "summary", "notes", "quiz", "revision"]))
        ):
            return IntentClassificationResult(
                intent="mixed",
                extracted_study_query=remainder,
                casual_greeting=prefix_match.group(0).strip(" ,.!"),
                reason="Greeting combined with study inquiry",
            )
        elif not remainder or is_casual_word or len(clean_rem.split()) <= 1:
            return IntentClassificationResult(
                intent="casual",
                reason="Casual greeting only",
            )

    # 4. Check if it's a short polite or acknowledgement query
    if len(normalized.split()) <= 2 and normalized in {
        "yes", "no", "sure", "yep", "nope", "alright", "perfect", "understood"
    }:
        return IntentClassificationResult(
            intent="casual",
            reason="Short acknowledgement",
        )

    # 5. Default to study intent
    return IntentClassificationResult(
        intent="study",
        extracted_study_query=cleaned,
        reason="Query contains study/document question",
    )


def generate_casual_response(query: str, classification: IntentClassificationResult) -> str:
    """
    Generates a natural, friendly, non-RAG response for casual student interactions.
    Does NOT invoke retrieval, reranking, or citations.
    """
    lower = query.strip().lower()
    norm = re.sub(r"[?!.,]+$", "", lower).strip()

    if norm in {"hi", "hello", "hey", "hey there", "good morning", "good afternoon", "good evening"}:
        return "Hi! Ready to study? What would you like to work on?"

    if norm in {"how are you", "how are you doing", "how's it going", "what's up", "whats up", "sup"}:
        return "I'm doing well! I'm ready to help you study. What would you like to explore?"

    if norm in {"what are you doing"}:
        return "I'm here and ready to help you explore your course materials, answer questions with citations, or create study guides. What are you working on today?"

    if norm in {"i'm tired", "im tired", "i am tired", "i'm sleepy", "i feel tired"}:
        return "Studying can be exhausting! Feel free to take a quick break or stretch. When you're ready, we can tackle one small topic at a time. What would you like to review?"

    if norm in {"thanks", "thank you", "thank you so much", "thx", "thanks a lot"}:
        return "You're very welcome! Let me know if you need more details on any topic or want to try practice questions."

    if norm in {"okay", "ok", "cool", "got it", "great", "awesome", "nice", "perfect", "understood"}:
        return "Sounds good! Whenever you have another question from your course material, just let me know."

    if norm in {"can you help me study", "can you help me study?", "help me study", "i want to study", "ready to study"}:
        return "Absolutely! Ask me anything about your uploaded course notes or PDFs, or explore the Revision Checklist, Study Guides, and Quizzes tabs. What topic shall we start with?"

    if "going to study" in lower:
        subject = classification.casual_greeting or "your material"
        if subject.strip() and subject != "today":
            clean_sub = subject.title().strip()
            return f"Great! I'm ready to help you with your {clean_sub} material. What would you like to learn?"
        return "Great! I'm ready to help you study. What topic or document would you like to start with?"

    return "Hello! I'm StudySpace AI, your academic assistant. Ask any question about your course materials or select a topic to begin studying!"
