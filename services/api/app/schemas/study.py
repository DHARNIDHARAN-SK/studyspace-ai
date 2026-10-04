from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

# ------------------------------------------------------------------------------
# Revision Checklist Schemas
# ------------------------------------------------------------------------------
RevisionStatus = Literal["not_started", "learning", "revised"]


class RevisionItemCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    description: Optional[str] = None
    status: RevisionStatus = "not_started"
    notes: Optional[str] = None


class RevisionItemUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=300)
    description: Optional[str] = None
    status: Optional[RevisionStatus] = None
    notes: Optional[str] = None


class RevisionLinkCreate(BaseModel):
    target_type: Literal["document", "chunk", "conversation", "message", "study_guide"]
    target_id: str
    metadata: Optional[Dict[str, Any]] = None


class RevisionLinkResponse(BaseModel):
    id: str
    revision_item_id: str
    target_type: str
    target_id: str
    metadata: Dict[str, Any] = {}
    created_at: datetime


class RevisionItemResponse(BaseModel):
    id: str
    workspace_id: str
    project_id: str
    user_id: str
    title: str
    description: Optional[str] = None
    status: RevisionStatus
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    links: List[RevisionLinkResponse] = []


class RevisionProgressStats(BaseModel):
    total_items: int
    not_started: int
    learning: int
    revised: int
    completion_percentage: float


class RevisionListResponse(BaseModel):
    items: List[RevisionItemResponse]
    stats: RevisionProgressStats


# ------------------------------------------------------------------------------
# Study Guide Schemas
# ------------------------------------------------------------------------------
class StudyGuideGenerateRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=300)
    guide_type: Literal["summary", "key_concepts", "formula_sheet", "definitions"] = "summary"
    focus_areas: Optional[List[str]] = None


class StudyGuideResponse(BaseModel):
    id: str
    workspace_id: str
    project_id: str
    title: str
    content: str
    guide_type: str
    source_citations: List[Dict[str, Any]] = []
    created_at: datetime
    updated_at: datetime


class StudyGuideListResponse(BaseModel):
    guides: List[StudyGuideResponse]
    total: int


# ------------------------------------------------------------------------------
# Quiz Schemas
# ------------------------------------------------------------------------------
class QuizGenerateRequest(BaseModel):
    title: Optional[str] = None
    topic: Optional[str] = None
    num_questions: int = Field(default=5, ge=1, le=20)
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    question_types: List[Literal["mcq", "short_answer", "difficult"]] = ["mcq", "short_answer", "difficult"]


class QuizQuestionPublicResponse(BaseModel):
    """Answers and explanations are intentionally hidden before submission."""
    id: str
    quiz_id: str
    question_type: str
    difficulty: str
    prompt: str
    options: Optional[List[str]] = None
    position: int


class QuizQuestionDetailResponse(BaseModel):
    """Full detail revealed after attempt submission."""
    id: str
    quiz_id: str
    question_type: str
    difficulty: str
    prompt: str
    options: Optional[List[str]] = None
    expected_answer: str
    explanation: str
    source_citations: List[Dict[str, Any]] = []
    position: int


class QuizResponse(BaseModel):
    id: str
    workspace_id: str
    project_id: str
    title: str
    status: str
    created_at: datetime
    questions: List[QuizQuestionPublicResponse] = []


class QuizDetailResponse(BaseModel):
    id: str
    workspace_id: str
    project_id: str
    title: str
    status: str
    created_at: datetime
    questions: List[QuizQuestionDetailResponse] = []


class QuizListResponse(BaseModel):
    quizzes: List[QuizResponse]
    total: int


class QuizSubmissionAnswer(BaseModel):
    question_id: str
    submitted_answer: str


class QuizSubmitRequest(BaseModel):
    responses: Optional[List[QuizSubmissionAnswer]] = None
    answers: Optional[List[QuizSubmissionAnswer]] = None


class QuestionResultResponse(BaseModel):
    question_id: str
    prompt: str
    question_type: str
    submitted_answer: str
    expected_answer: str
    is_correct: bool
    explanation: str
    feedback: str
    source_citations: List[Dict[str, Any]] = []


class QuizAttemptResultResponse(BaseModel):
    attempt_id: str
    quiz_id: str
    score: float
    total_questions: int
    correct_count: int
    percentage: float
    started_at: datetime
    completed_at: datetime
    results: List[QuestionResultResponse]


class QuizAttemptSummaryResponse(BaseModel):
    id: str
    quiz_id: str
    score: Optional[float] = None
    total_questions: int
    started_at: datetime
    completed_at: Optional[datetime] = None


# ------------------------------------------------------------------------------
# Export Schemas
# ------------------------------------------------------------------------------
class ExportRequest(BaseModel):
    source_type: Literal["study_guide", "quiz", "revision"]
    source_id: str
    format: Literal["markdown", "txt", "pdf", "docx"] = "markdown"


class ExportResponse(BaseModel):
    id: str
    source_type: str
    source_id: str
    format: str
    status: str
    content: Optional[str] = None
    filename: str
    created_at: datetime
