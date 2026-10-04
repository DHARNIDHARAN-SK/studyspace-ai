from datetime import datetime, timezone
import json
import re
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy import select, delete, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.errors import AppError, NotFoundError, ForbiddenError
from app.core.logging import logger
from app.db.models import (
    Document,
    DocumentChunk,
    Export,
    Profile,
    Project,
    Quiz,
    QuizAttempt,
    QuizQuestion,
    QuizResponse,
    RevisionItem,
    RevisionItemLink,
    StudyGuide,
    Workspace,
)
from app.db.repository import store
from app.db.session import get_session_factory
from app.rag.context.builder import ContextBuilder
from app.rag.llm.registry import get_llm_provider
from app.rag.retrieval.hybrid_retriever import HybridRetriever
from app.rag.retrieval.vector_retriever import VectorRetriever
from app.schemas.study import (
    ExportResponse,
    QuestionResultResponse,
    QuizAttemptResultResponse,
    QuizAttemptSummaryResponse,
    QuizDetailResponse,
    QuizListResponse,
    QuizQuestionDetailResponse,
    QuizQuestionPublicResponse,
    QuizResponse as QuizSchemaResponse,
    QuizSubmissionAnswer,
    RevisionItemCreate,
    RevisionItemResponse,
    RevisionItemUpdate,
    RevisionLinkCreate,
    RevisionLinkResponse,
    RevisionListResponse,
    RevisionProgressStats,
    StudyGuideListResponse,
    StudyGuideResponse,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_uuid(val: Any) -> Optional[uuid.UUID]:
    try:
        return uuid.UUID(str(val))
    except (ValueError, TypeError, AttributeError):
        return None


class StudyService:
    """
    Manages Phase 10 student intelligence features:
    - Revision Checklist & Progress Tracking
    - Grounded Study Guide Generation
    - Quiz Generation, Interactive Assessment & Grading
    - Source & Citation Linking
    - Markdown / Text / Document Export
    """

    def __init__(self):
        self.context_builder = ContextBuilder(max_context_chars=8000)

    # --------------------------------------------------------------------------
    # Revision Checklist
    # --------------------------------------------------------------------------
    async def create_revision_item(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        data: RevisionItemCreate,
        db: Optional[AsyncSession] = None,
    ) -> RevisionItemResponse:
        now = utc_now()
        item_id = uuid.uuid4()

        item_dict = {
            "id": str(item_id),
            "workspace_id": str(workspace_id),
            "project_id": str(project_id),
            "user_id": str(user_id),
            "title": data.title,
            "description": data.description,
            "status": data.status,
            "notes": data.notes,
            "created_at": now,
            "updated_at": now,
            "links": [],
        }
        store.revision_items[str(item_id)] = item_dict

        if db is not None:
            try:
                db_item = RevisionItem(
                    id=item_id,
                    workspace_id=workspace_id,
                    project_id=project_id,
                    user_id=user_id,
                    title=data.title,
                    description=data.description,
                    status=data.status,
                    notes=data.notes,
                    created_at=now,
                    updated_at=now,
                )
                db.add(db_item)
                await db.commit()
            except Exception as e:
                logger.warning("Failed to persist revision item in DB: %s", e)

        return RevisionItemResponse(
            id=str(item_id),
            workspace_id=str(workspace_id),
            project_id=str(project_id),
            user_id=str(user_id),
            title=data.title,
            description=data.description,
            status=data.status,
            notes=data.notes,
            created_at=now,
            updated_at=now,
            links=[],
        )

    async def list_revision_items(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        db: Optional[AsyncSession] = None,
    ) -> RevisionListResponse:
        items_map: Dict[str, dict] = {}

        # 1. Load from DB if available
        if db is not None:
            try:
                stmt = (
                    select(RevisionItem)
                    .options(selectinload(RevisionItem.links))
                    .where(
                        RevisionItem.project_id == project_id,
                        RevisionItem.workspace_id == workspace_id,
                    )
                    .order_by(RevisionItem.created_at.asc())
                )
                res = await db.execute(stmt)
                db_items = res.scalars().all()
                for item in db_items:
                    str_id = str(item.id)
                    links_data = [
                        {
                            "id": str(l.id),
                            "revision_item_id": str(l.revision_item_id),
                            "target_type": l.target_type,
                            "target_id": str(l.target_id),
                            "metadata": l.metadata_ or {},
                            "created_at": l.created_at,
                        }
                        for l in item.links
                    ]
                    items_map[str_id] = {
                        "id": str_id,
                        "workspace_id": str(item.workspace_id),
                        "project_id": str(item.project_id),
                        "user_id": str(item.user_id),
                        "title": item.title,
                        "description": item.description,
                        "status": item.status,
                        "notes": item.notes,
                        "created_at": item.created_at,
                        "updated_at": item.updated_at,
                        "links": links_data,
                    }
                    store.revision_items[str_id] = items_map[str_id]
            except Exception as e:
                logger.warning("Failed to query revision items from DB: %s", e)

        # 2. Merge with memory store
        for item_id, item in store.revision_items.items():
            if item.get("project_id") == str(project_id) and item_id not in items_map:
                items_map[item_id] = item

        items_list = list(items_map.values())
        items_list.sort(key=lambda x: str(x.get("created_at", "")))

        # 3. Calculate statistics
        total = len(items_list)
        not_started = sum(1 for i in items_list if i.get("status") == "not_started")
        learning = sum(1 for i in items_list if i.get("status") == "learning")
        revised = sum(1 for i in items_list if i.get("status") == "revised")
        completion_pct = round((revised / total * 100.0), 1) if total > 0 else 0.0

        responses = [
            RevisionItemResponse(
                id=i["id"],
                workspace_id=i["workspace_id"],
                project_id=i["project_id"],
                user_id=i["user_id"],
                title=i["title"],
                description=i.get("description"),
                status=i["status"],
                notes=i.get("notes"),
                created_at=i["created_at"],
                updated_at=i["updated_at"],
                links=[
                    RevisionLinkResponse(
                        id=l["id"],
                        revision_item_id=l["revision_item_id"],
                        target_type=l["target_type"],
                        target_id=str(l["target_id"]),
                        metadata=l.get("metadata", {}),
                        created_at=l["created_at"],
                    )
                    for l in i.get("links", [])
                ],
            )
            for i in items_list
        ]

        return RevisionListResponse(
            items=responses,
            stats=RevisionProgressStats(
                total_items=total,
                not_started=not_started,
                learning=learning,
                revised=revised,
                completion_percentage=completion_pct,
            ),
        )

    async def update_revision_item(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        item_id: uuid.UUID,
        data: RevisionItemUpdate,
        db: Optional[AsyncSession] = None,
    ) -> RevisionItemResponse:
        str_id = str(item_id)
        now = utc_now()

        item = store.revision_items.get(str_id)
        if not item and db is None:
            raise NotFoundError(f"Revision item {item_id} not found.")

        if db is not None:
            db_item = await db.get(RevisionItem, item_id)
            if not db_item:
                raise NotFoundError(f"Revision item {item_id} not found.")
            if db_item.project_id != project_id or db_item.workspace_id != workspace_id:
                raise ForbiddenError("Access to revision item denied.")

            if data.title is not None:
                db_item.title = data.title
            if data.description is not None:
                db_item.description = data.description
            if data.status is not None:
                db_item.status = data.status
            if data.notes is not None:
                db_item.notes = data.notes
            db_item.updated_at = now
            await db.commit()

            # Refresh links
            stmt = select(RevisionItemLink).where(RevisionItemLink.revision_item_id == item_id)
            res = await db.execute(stmt)
            db_links = res.scalars().all()
            links_data = [
                {
                    "id": str(l.id),
                    "revision_item_id": str(l.revision_item_id),
                    "target_type": l.target_type,
                    "target_id": str(l.target_id),
                    "metadata": l.metadata_ or {},
                    "created_at": l.created_at,
                }
                for l in db_links
            ]

            item = {
                "id": str_id,
                "workspace_id": str(db_item.workspace_id),
                "project_id": str(db_item.project_id),
                "user_id": str(db_item.user_id),
                "title": db_item.title,
                "description": db_item.description,
                "status": db_item.status,
                "notes": db_item.notes,
                "created_at": db_item.created_at,
                "updated_at": db_item.updated_at,
                "links": links_data,
            }
            store.revision_items[str_id] = item
        else:
            if item["project_id"] != str(project_id) or item["workspace_id"] != str(workspace_id):
                raise ForbiddenError("Access to revision item denied.")
            if data.title is not None:
                item["title"] = data.title
            if data.description is not None:
                item["description"] = data.description
            if data.status is not None:
                item["status"] = data.status
            if data.notes is not None:
                item["notes"] = data.notes
            item["updated_at"] = now

        return RevisionItemResponse(
            id=item["id"],
            workspace_id=item["workspace_id"],
            project_id=item["project_id"],
            user_id=item["user_id"],
            title=item["title"],
            description=item.get("description"),
            status=item["status"],
            notes=item.get("notes"),
            created_at=item["created_at"],
            updated_at=item["updated_at"],
            links=[
                RevisionLinkResponse(
                    id=l["id"],
                    revision_item_id=l["revision_item_id"],
                    target_type=l["target_type"],
                    target_id=str(l["target_id"]),
                    metadata=l.get("metadata", {}),
                    created_at=l["created_at"],
                )
                for l in item.get("links", [])
            ],
        )

    async def delete_revision_item(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        item_id: uuid.UUID,
        db: Optional[AsyncSession] = None,
    ) -> None:
        str_id = str(item_id)
        if str_id in store.revision_items:
            del store.revision_items[str_id]

        if db is not None:
            db_item = await db.get(RevisionItem, item_id)
            if db_item:
                if db_item.project_id != project_id or db_item.workspace_id != workspace_id:
                    raise ForbiddenError("Access to revision item denied.")
                await db.delete(db_item)
                await db.commit()

    async def add_revision_link(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        item_id: uuid.UUID,
        data: RevisionLinkCreate,
        db: Optional[AsyncSession] = None,
    ) -> RevisionLinkResponse:
        link_id = uuid.uuid4()
        now = utc_now()

        link_dict = {
            "id": str(link_id),
            "revision_item_id": str(item_id),
            "target_type": data.target_type,
            "target_id": data.target_id,
            "metadata": data.metadata or {},
            "created_at": now,
        }

        # Update in-memory item
        str_item_id = str(item_id)
        if str_item_id in store.revision_items:
            store.revision_items[str_item_id].setdefault("links", []).append(link_dict)

        if db is not None:
            target_uuid = _to_uuid(data.target_id) or uuid.uuid4()
            db_link = RevisionItemLink(
                id=link_id,
                revision_item_id=item_id,
                target_type=data.target_type,
                target_id=target_uuid,
                metadata_=data.metadata or {},
                created_at=now,
            )
            db.add(db_link)
            await db.commit()

        return RevisionLinkResponse(**link_dict)

    # --------------------------------------------------------------------------
    # Study Guides
    # --------------------------------------------------------------------------
    async def generate_study_guide(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        topic: str,
        guide_type: str = "summary",
        focus_areas: Optional[List[str]] = None,
        db: Optional[AsyncSession] = None,
    ) -> StudyGuideResponse:
        now = utc_now()
        guide_id = uuid.uuid4()

        # 1. Retrieve project evidence via RAG
        retrieved_chunks = []
        citations_data = []
        try:
            retriever = HybridRetriever()
            ret_res = await retriever.retrieve(
                query=topic,
                workspace_id=workspace_id,
                project_id=project_id,
                top_k=6,
            )
            retrieved_chunks = ret_res.chunks
        except Exception:
            try:
                dense_retriever = VectorRetriever()
                retrieved_chunks = await dense_retriever.retrieve(
                    query=topic,
                    workspace_id=workspace_id,
                    project_id=project_id,
                    top_k=6,
                )
            except Exception as e:
                logger.warning("Retrieval failed during study guide generation: %s", e)

        # 2. Build context
        if retrieved_chunks:
            built_context = self.context_builder.build_context(retrieved_chunks)
            context_text = built_context.text
            for c in built_context.citations:
                citations_data.append({
                    "document_id": str(c.document_id),
                    "document_title": c.document_title,
                    "page_start": c.page_start,
                    "page_end": c.page_end,
                    "section_path": c.section_path or "",
                    "snippet": c.snippet,
                    "similarity_score": c.similarity_score,
                    "citation_label": c.citation_label,
                })
        else:
            context_text = f"Study material on the topic: {topic}."

        # 3. Prompt LLM or use structured academic synthesis
        prompt = (
            f"Generate a comprehensive, high-yield academic study guide for students studying: '{topic}'.\n"
            f"Guide Type: {guide_type}\n"
            f"Focus Areas: {', '.join(focus_areas) if focus_areas else 'Core principles, architectures, and key terminology'}\n\n"
            f"Context Evidence:\n{context_text}\n\n"
            "Format the guide using clean Markdown with:\n"
            "# Study Guide: " + topic + "\n"
            "## 1. Executive Summary & Overview\n"
            "## 2. Core Concepts & Architecture\n"
            "## 3. Key Terminology & Definitions\n"
            "## 4. Deep-Dive Explanations & Evidence\n"
            "## 5. Review Checklist & Exam Practice Questions\n"
        )

        content = ""
        try:
            llm = get_llm_provider()
            resp = await llm.generate(
                prompt=prompt,
                system_prompt="You are an expert university professor and pedagogical study guide creator. Ground all answers strictly in the provided materials.",
                max_tokens=2500,
                temperature=0.2,
            )
            content = resp.content
        except Exception as e:
            logger.warning("LLM call failed for study guide, generating grounded fallback: %s", e)
            content = (
                f"# Study Guide: {topic}\n\n"
                f"## 1. Executive Summary & Overview\n"
                f"This study guide reviews the foundational principles and technical mechanisms of **{topic}** "
                f"based on project course materials.\n\n"
                f"## 2. Core Concepts & Architecture\n"
                f"- **Core Theory**: Foundational models, service paradigms, and resource abstractions.\n"
                f"- **Operational Models**: Practical deployments, lifecycle management, and architectural boundaries.\n\n"
                f"## 3. Key Terminology\n"
                f"- **{topic}**: Primary domain focus covering key definitions and practical application.\n"
                f"- **Virtualization & Abstraction**: Mechanism for decoupled resource provisioning.\n\n"
                f"## 4. Grounded Course Material Excerpts\n"
                f"{context_text[:2000]}\n\n"
                f"## 5. Revision Checklist\n"
                f"- [ ] Explain the key characteristics of {topic}.\n"
                f"- [ ] Compare and contrast operational trade-offs.\n"
                f"- [ ] Review architectural diagrams and source citations.\n"
            )

        title = f"{topic} — Study Guide"
        guide_dict = {
            "id": str(guide_id),
            "workspace_id": str(workspace_id),
            "project_id": str(project_id),
            "title": title,
            "content": content,
            "guide_type": guide_type,
            "source_citations": citations_data,
            "created_at": now,
            "updated_at": now,
        }
        store.study_guides[str(guide_id)] = guide_dict

        if db is not None:
            try:
                db_guide = StudyGuide(
                    id=guide_id,
                    workspace_id=workspace_id,
                    project_id=project_id,
                    created_by_user_id=user_id,
                    title=title,
                    content=content,
                    guide_type=guide_type,
                    source_citations=citations_data,
                    created_at=now,
                    updated_at=now,
                )
                db.add(db_guide)
                await db.commit()
            except Exception as e:
                logger.warning("Failed to persist study guide in DB: %s", e)

        return StudyGuideResponse(
            id=str(guide_id),
            workspace_id=str(workspace_id),
            project_id=str(project_id),
            title=title,
            content=content,
            guide_type=guide_type,
            source_citations=citations_data,
            created_at=now,
            updated_at=now,
        )

    async def list_study_guides(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        db: Optional[AsyncSession] = None,
    ) -> StudyGuideListResponse:
        guides_map: Dict[str, dict] = {}

        if db is not None:
            try:
                stmt = (
                    select(StudyGuide)
                    .where(
                        StudyGuide.project_id == project_id,
                        StudyGuide.workspace_id == workspace_id,
                    )
                    .order_by(StudyGuide.created_at.desc())
                )
                res = await db.execute(stmt)
                db_guides = res.scalars().all()
                for g in db_guides:
                    str_id = str(g.id)
                    guides_map[str_id] = {
                        "id": str_id,
                        "workspace_id": str(g.workspace_id),
                        "project_id": str(g.project_id),
                        "title": g.title,
                        "content": g.content,
                        "guide_type": g.guide_type,
                        "source_citations": g.source_citations or [],
                        "created_at": g.created_at,
                        "updated_at": g.updated_at,
                    }
                    store.study_guides[str_id] = guides_map[str_id]
            except Exception as e:
                logger.warning("Failed to query study guides from DB: %s", e)

        for gid, g in store.study_guides.items():
            if g.get("project_id") == str(project_id) and gid not in guides_map:
                guides_map[gid] = g

        guides = [StudyGuideResponse(**g) for g in guides_map.values()]
        return StudyGuideListResponse(guides=guides, total=len(guides))

    async def get_study_guide(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        guide_id: uuid.UUID,
        db: Optional[AsyncSession] = None,
    ) -> StudyGuideResponse:
        str_id = str(guide_id)
        if db is not None:
            db_guide = await db.get(StudyGuide, guide_id)
            if db_guide:
                if db_guide.project_id != project_id or db_guide.workspace_id != workspace_id:
                    raise ForbiddenError("Access to study guide denied.")
                return StudyGuideResponse(
                    id=str(db_guide.id),
                    workspace_id=str(db_guide.workspace_id),
                    project_id=str(db_guide.project_id),
                    title=db_guide.title,
                    content=db_guide.content,
                    guide_type=db_guide.guide_type,
                    source_citations=db_guide.source_citations or [],
                    created_at=db_guide.created_at,
                    updated_at=db_guide.updated_at,
                )

        g = store.study_guides.get(str_id)
        if not g:
            raise NotFoundError(f"Study guide {guide_id} not found.")
        if g["project_id"] != str(project_id) or g["workspace_id"] != str(workspace_id):
            raise ForbiddenError("Access to study guide denied.")

        return StudyGuideResponse(**g)

    # --------------------------------------------------------------------------
    # Quizzes
    # --------------------------------------------------------------------------
    async def generate_quiz(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        title: Optional[str] = None,
        topic: Optional[str] = None,
        num_questions: int = 5,
        difficulty: str = "medium",
        question_types: Optional[List[str]] = None,
        db: Optional[AsyncSession] = None,
    ) -> QuizSchemaResponse:
        now = utc_now()
        quiz_id = uuid.uuid4()
        types = question_types or ["mcq", "short_answer", "difficult"]
        quiz_title = title or f"{topic or 'Course Materials'} — Practice Quiz"

        # 1. Retrieve chunks
        search_query = topic or "key concepts, definitions, architecture, and principles"
        retrieved_chunks = []
        try:
            retriever = HybridRetriever()
            ret_res = await retriever.retrieve(
                query=search_query,
                workspace_id=workspace_id,
                project_id=project_id,
                top_k=8,
            )
            retrieved_chunks = ret_res.chunks
        except Exception:
            try:
                dense_retriever = VectorRetriever()
                retrieved_chunks = await dense_retriever.retrieve(
                    query=search_query,
                    workspace_id=workspace_id,
                    project_id=project_id,
                    top_k=8,
                )
            except Exception as e:
                logger.warning("Retrieval failed during quiz generation: %s", e)

        # 2. Build questions
        questions_raw = []

        # Determine mix of types
        desired_types = []
        for i in range(num_questions):
            desired_types.append(types[i % len(types)])

        # Construct generation prompt for LLM
        prompt = (
            f"Generate a {num_questions}-question academic quiz for university students based on these materials.\n"
            f"Topic: {topic or 'Course Concepts'}\n"
            f"Difficulty: {difficulty}\n"
            f"Required Question Types: {desired_types}\n\n"
            "Format the response strictly as valid JSON matching this schema:\n"
            "[\n"
            "  {\n"
            '    "question_type": "mcq" | "short_answer" | "difficult",\n'
            '    "difficulty": "easy" | "medium" | "hard",\n'
            '    "prompt": "Question text...",\n'
            '    "options": ["A) ...", "B) ...", "C) ...", "D) ..."] (only for mcq),\n'
            '    "expected_answer": "A" (or exact answer string),\n'
            '    "explanation": "Detailed pedagogical explanation citing why this is correct."\n'
            "  }\n"
            "]\n\n"
            f"Context Evidence:\n"
            f"{self.context_builder.build_context(retrieved_chunks).text[:6000] if retrieved_chunks else 'Cloud computing and systems fundamentals.'}\n"
        )

        try:
            llm = get_llm_provider()
            resp = await llm.generate(
                prompt=prompt,
                system_prompt="You are a strict, objective university exam author. Produce valid JSON questions only.",
                max_tokens=3000,
                temperature=0.2,
            )
            # Parse JSON
            raw_text = resp.content.strip()
            # Clean markdown code blocks if wrapped
            if "```" in raw_text:
                m = re.search(r"```(?:json)?(.*?)```", raw_text, re.DOTALL)
                if m:
                    raw_text = m.group(1).strip()
            parsed = json.loads(raw_text)
            if isinstance(parsed, list):
                questions_raw = parsed[:num_questions]
        except Exception as e:
            logger.warning("LLM question generation failed or invalid JSON: %s. Using high-yield fallback questions.", e)

        # Fallback question generation if LLM was unavailable
        if not questions_raw or len(questions_raw) == 0:
            questions_raw = [
                {
                    "question_type": "mcq",
                    "difficulty": "medium",
                    "prompt": f"According to the course materials on {topic or 'Cloud Computing'}, which model provides virtualized hardware resources over a network?",
                    "options": [
                        "A) Infrastructure as a Service (IaaS)",
                        "B) Software as a Service (SaaS)",
                        "C) Platform as a Service (PaaS)",
                        "D) Function as a Service (FaaS)",
                    ],
                    "expected_answer": "A",
                    "explanation": "IaaS provides on-demand access to fundamental computing resources like virtual machines, storage, and networking.",
                },
                {
                    "question_type": "short_answer",
                    "difficulty": "medium",
                    "prompt": f"What is the primary role of a hypervisor in cloud virtualization architectures?",
                    "options": None,
                    "expected_answer": "Hardware virtualization and guest OS management",
                    "explanation": "A hypervisor (or Virtual Machine Monitor) abstracts hardware, allowing multiple guest operating systems to share physical resources safely.",
                },
                {
                    "question_type": "difficult",
                    "difficulty": "hard",
                    "prompt": f"In a multi-tenant cloud environment, how does the shared responsibility security model divide accountability between the cloud provider and the customer?",
                    "options": None,
                    "expected_answer": "The provider secures the infrastructure (cloud itself), while the customer secures data, access, and guest configurations (in the cloud).",
                    "explanation": "The cloud provider secures physical facilities, hardware, and hypervisors, while customers are responsible for identity, access management, encryption, and application software.",
                },
            ]

        # 3. Save Quiz and Questions
        created_questions = []
        for idx, q_data in enumerate(questions_raw, start=1):
            q_id = uuid.uuid4()
            q_dict = {
                "id": str(q_id),
                "quiz_id": str(quiz_id),
                "question_type": q_data.get("question_type", "mcq"),
                "difficulty": q_data.get("difficulty", difficulty),
                "prompt": q_data.get("prompt", "Question prompt"),
                "options": q_data.get("options"),
                "expected_answer": str(q_data.get("expected_answer", "")),
                "explanation": str(q_data.get("explanation", "")),
                "source_citations": [
                    {
                        "document_title": c.document_title,
                        "page_start": c.page_start,
                        "citation_label": c.citation_label,
                    }
                    for c in retrieved_chunks[:2]
                ] if retrieved_chunks else [],
                "position": idx,
                "created_at": now,
            }
            created_questions.append(q_dict)
            store.quiz_questions[str(q_id)] = q_dict

        quiz_dict = {
            "id": str(quiz_id),
            "workspace_id": str(workspace_id),
            "project_id": str(project_id),
            "title": quiz_title,
            "status": "ready",
            "created_at": now,
            "questions": created_questions,
        }
        store.quizzes[str(quiz_id)] = quiz_dict

        if db is not None:
            try:
                db_quiz = Quiz(
                    id=quiz_id,
                    workspace_id=workspace_id,
                    project_id=project_id,
                    created_by_user_id=user_id,
                    title=quiz_title,
                    status="ready",
                    created_at=now,
                    updated_at=now,
                )
                db.add(db_quiz)
                await db.flush()

                for q in created_questions:
                    db_q = QuizQuestion(
                        id=uuid.UUID(q["id"]),
                        quiz_id=quiz_id,
                        question_type=q["question_type"],
                        difficulty=q["difficulty"],
                        prompt=q["prompt"],
                        options=q["options"],
                        expected_answer=q["expected_answer"],
                        explanation=q["explanation"],
                        source_citations=q["source_citations"],
                        position=q["position"],
                        created_at=now,
                    )
                    db.add(db_q)
                await db.commit()
            except Exception as e:
                logger.warning("Failed to persist quiz in DB: %s", e)

        # Public quiz response hides expected_answer and explanation!
        return QuizSchemaResponse(
            id=str(quiz_id),
            workspace_id=str(workspace_id),
            project_id=str(project_id),
            title=quiz_title,
            status="ready",
            created_at=now,
            questions=[
                QuizQuestionPublicResponse(
                    id=q["id"],
                    quiz_id=q["quiz_id"],
                    question_type=q["question_type"],
                    difficulty=q["difficulty"],
                    prompt=q["prompt"],
                    options=q["options"],
                    position=q["position"],
                )
                for q in created_questions
            ],
        )

    async def list_quizzes(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        db: Optional[AsyncSession] = None,
    ) -> QuizListResponse:
        quizzes_map: Dict[str, dict] = {}

        if db is not None:
            try:
                stmt = (
                    select(Quiz)
                    .options(selectinload(Quiz.questions))
                    .where(
                        Quiz.project_id == project_id,
                        Quiz.workspace_id == workspace_id,
                    )
                    .order_by(Quiz.created_at.desc())
                )
                res = await db.execute(stmt)
                db_quizzes = res.scalars().all()
                for q in db_quizzes:
                    str_id = str(q.id)
                    q_list = [
                        {
                            "id": str(ques.id),
                            "quiz_id": str(ques.quiz_id),
                            "question_type": ques.question_type,
                            "difficulty": ques.difficulty,
                            "prompt": ques.prompt,
                            "options": ques.options,
                            "expected_answer": ques.expected_answer,
                            "explanation": ques.explanation,
                            "source_citations": ques.source_citations or [],
                            "position": ques.position,
                            "created_at": ques.created_at,
                        }
                        for ques in q.questions
                    ]
                    quizzes_map[str_id] = {
                        "id": str_id,
                        "workspace_id": str(q.workspace_id),
                        "project_id": str(q.project_id),
                        "title": q.title,
                        "status": q.status,
                        "created_at": q.created_at,
                        "questions": q_list,
                    }
                    store.quizzes[str_id] = quizzes_map[str_id]
            except Exception as e:
                logger.warning("Failed to query quizzes from DB: %s", e)

        for qid, q in store.quizzes.items():
            if q.get("project_id") == str(project_id) and qid not in quizzes_map:
                quizzes_map[qid] = q

        out = []
        for q in quizzes_map.values():
            out.append(
                QuizSchemaResponse(
                    id=q["id"],
                    workspace_id=q["workspace_id"],
                    project_id=q["project_id"],
                    title=q["title"],
                    status=q["status"],
                    created_at=q["created_at"],
                    questions=[
                        QuizQuestionPublicResponse(
                            id=ques["id"],
                            quiz_id=ques["quiz_id"],
                            question_type=ques["question_type"],
                            difficulty=ques["difficulty"],
                            prompt=ques["prompt"],
                            options=ques.get("options"),
                            position=ques["position"],
                        )
                        for ques in q.get("questions", [])
                    ],
                )
            )

        return QuizListResponse(quizzes=out, total=len(out))

    async def get_quiz(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        quiz_id: uuid.UUID,
        include_answers: bool = False,
        db: Optional[AsyncSession] = None,
    ) -> Any:
        str_id = str(quiz_id)

        # Ensure loaded
        quiz_dict = store.quizzes.get(str_id)
        if not quiz_dict and db is not None:
            stmt = (
                select(Quiz)
                .options(selectinload(Quiz.questions))
                .where(Quiz.id == quiz_id)
            )
            res = await db.execute(stmt)
            q = res.scalars().first()
            if q:
                if q.project_id != project_id or q.workspace_id != workspace_id:
                    raise ForbiddenError("Access to quiz denied.")
                q_list = [
                    {
                        "id": str(ques.id),
                        "quiz_id": str(ques.quiz_id),
                        "question_type": ques.question_type,
                        "difficulty": ques.difficulty,
                        "prompt": ques.prompt,
                        "options": ques.options,
                        "expected_answer": ques.expected_answer,
                        "explanation": ques.explanation,
                        "source_citations": ques.source_citations or [],
                        "position": ques.position,
                        "created_at": ques.created_at,
                    }
                    for ques in q.questions
                ]
                quiz_dict = {
                    "id": str_id,
                    "workspace_id": str(q.workspace_id),
                    "project_id": str(q.project_id),
                    "title": q.title,
                    "status": q.status,
                    "created_at": q.created_at,
                    "questions": q_list,
                }
                store.quizzes[str_id] = quiz_dict

        if not quiz_dict:
            raise NotFoundError(f"Quiz {quiz_id} not found.")

        if quiz_dict["project_id"] != str(project_id) or quiz_dict["workspace_id"] != str(workspace_id):
            raise ForbiddenError("Access to quiz denied.")

        if include_answers:
            return QuizDetailResponse(
                id=quiz_dict["id"],
                workspace_id=quiz_dict["workspace_id"],
                project_id=quiz_dict["project_id"],
                title=quiz_dict["title"],
                status=quiz_dict["status"],
                created_at=quiz_dict["created_at"],
                questions=[
                    QuizQuestionDetailResponse(**ques)
                    for ques in quiz_dict.get("questions", [])
                ],
            )

        return QuizSchemaResponse(
            id=quiz_dict["id"],
            workspace_id=quiz_dict["workspace_id"],
            project_id=quiz_dict["project_id"],
            title=quiz_dict["title"],
            status=quiz_dict["status"],
            created_at=quiz_dict["created_at"],
            questions=[
                QuizQuestionPublicResponse(
                    id=ques["id"],
                    quiz_id=ques["quiz_id"],
                    question_type=ques["question_type"],
                    difficulty=ques["difficulty"],
                    prompt=ques["prompt"],
                    options=ques.get("options"),
                    position=ques["position"],
                )
                for ques in quiz_dict.get("questions", [])
            ],
        )

    async def submit_quiz_attempt(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        quiz_id: uuid.UUID,
        responses: List[QuizSubmissionAnswer],
        db: Optional[AsyncSession] = None,
    ) -> QuizAttemptResultResponse:
        # Load detailed quiz with answers
        quiz_detail: QuizDetailResponse = await self.get_quiz(
            user_id=user_id,
            workspace_id=workspace_id,
            project_id=project_id,
            quiz_id=quiz_id,
            include_answers=True,
            db=db,
        )

        now = utc_now()
        attempt_id = uuid.uuid4()
        question_lookup = {q.id: q for q in quiz_detail.questions}
        submitted_lookup = {r.question_id: r.submitted_answer for r in responses}

        results: List[QuestionResultResponse] = []
        correct_count = 0
        total_questions = len(quiz_detail.questions)

        for q in quiz_detail.questions:
            student_ans = submitted_lookup.get(q.id, "").strip()
            exp_ans = q.expected_answer.strip()

            is_correct = False
            feedback = ""

            if q.question_type == "mcq":
                # Compare option letter (e.g. "A" in "A) ...")
                clean_student = student_ans.split(")")[0].strip().upper() if student_ans else ""
                clean_exp = exp_ans.split(")")[0].strip().upper()
                if clean_student == clean_exp or (student_ans.lower() == exp_ans.lower()):
                    is_correct = True
                    feedback = "Correct! Well reasoned."
                else:
                    feedback = f"Incorrect. The correct option is {exp_ans}."
            else:
                # Conceptual matching: check keyword presence or non-empty substantial answer
                key_terms = [t.lower() for t in exp_ans.split() if len(t) > 3]
                matches = sum(1 for t in key_terms if t in student_ans.lower())
                if student_ans and (matches >= max(1, len(key_terms) // 3) or exp_ans.lower() in student_ans.lower()):
                    is_correct = True
                    feedback = "Accurate! Key conceptual components successfully addressed."
                elif student_ans:
                    feedback = f"Partially accurate or missing key concepts. Expected: '{exp_ans}'."
                else:
                    feedback = f"No answer provided. Expected: '{exp_ans}'."

            if is_correct:
                correct_count += 1

            results.append(
                QuestionResultResponse(
                    question_id=q.id,
                    prompt=q.prompt,
                    question_type=q.question_type,
                    submitted_answer=student_ans,
                    expected_answer=q.expected_answer,
                    is_correct=is_correct,
                    explanation=q.explanation,
                    feedback=feedback,
                    source_citations=q.source_citations,
                )
            )

        score_pct = round((correct_count / total_questions * 100.0), 1) if total_questions > 0 else 0.0

        attempt_dict = {
            "id": str(attempt_id),
            "quiz_id": str(quiz_id),
            "score": score_pct,
            "total_questions": total_questions,
            "correct_count": correct_count,
            "percentage": score_pct,
            "started_at": now,
            "completed_at": now,
            "results": [r.model_dump() for r in results],
        }
        store.quiz_attempts[str(attempt_id)] = attempt_dict

        if db is not None:
            try:
                db_attempt = QuizAttempt(
                    id=attempt_id,
                    quiz_id=quiz_id,
                    workspace_id=workspace_id,
                    user_id=user_id,
                    started_at=now,
                    completed_at=now,
                    score=score_pct,
                    total_questions=total_questions,
                )
                db.add(db_attempt)
                await db.flush()

                for r in results:
                    q_uuid = _to_uuid(r.question_id)
                    if q_uuid:
                        db_resp = QuizResponse(
                            id=uuid.uuid4(),
                            quiz_attempt_id=attempt_id,
                            question_id=q_uuid,
                            submitted_answer=r.submitted_answer,
                            is_correct=r.is_correct,
                            feedback=r.feedback,
                            created_at=now,
                        )
                        db.add(db_resp)
                await db.commit()
            except Exception as e:
                logger.warning("Failed to persist quiz attempt in DB: %s", e)

        return QuizAttemptResultResponse(
            attempt_id=str(attempt_id),
            quiz_id=str(quiz_id),
            score=score_pct,
            total_questions=total_questions,
            correct_count=correct_count,
            percentage=score_pct,
            started_at=now,
            completed_at=now,
            results=results,
        )

    # --------------------------------------------------------------------------
    # Export Formatting
    # --------------------------------------------------------------------------
    async def export_content(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        source_type: str,
        source_id: str,
        format_type: str = "markdown",
        db: Optional[AsyncSession] = None,
    ) -> ExportResponse:
        export_id = uuid.uuid4()
        now = utc_now()
        content = ""
        filename = f"studyspace-export-{now.strftime('%Y%m%d-%H%M%S')}"

        if source_type == "study_guide":
            guide_uuid = _to_uuid(source_id)
            if not guide_uuid:
                raise AppError("Invalid study guide ID.", status_code=400)
            guide = await self.get_study_guide(user_id, workspace_id, project_id, guide_uuid, db=db)
            filename = f"study-guide-{re.sub(r'[^a-zA-Z0-9_-]', '_', guide.title).lower()}"
            content = guide.content

        elif source_type == "quiz":
            quiz_uuid = _to_uuid(source_id)
            if not quiz_uuid:
                raise AppError("Invalid quiz ID.", status_code=400)
            quiz = await self.get_quiz(user_id, workspace_id, project_id, quiz_uuid, include_answers=True, db=db)
            filename = f"quiz-{re.sub(r'[^a-zA-Z0-9_-]', '_', quiz.title).lower()}"
            
            lines = [f"# {quiz.title}\n", f"Generated: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"]
            for idx, q in enumerate(quiz.questions, start=1):
                lines.append(f"### Question {idx} ({q.difficulty.capitalize()} - {q.question_type.upper()})")
                lines.append(q.prompt)
                if q.options:
                    for opt in q.options:
                        lines.append(f"- {opt}")
                lines.append(f"\n**Answer**: {q.expected_answer}")
                lines.append(f"**Explanation**: {q.explanation}\n")
            content = "\n".join(lines)

        elif source_type == "revision":
            revision_res = await self.list_revision_items(user_id, workspace_id, project_id, db=db)
            filename = f"revision-checklist-{now.strftime('%Y%m%d')}"
            lines = [
                "# Revision Checklist\n",
                f"**Completion**: {revision_res.stats.completion_percentage}% ({revision_res.stats.revised}/{revision_res.stats.total_items} revised)\n",
            ]
            for item in revision_res.items:
                marker = "[x]" if item.status == "revised" else "[-]" if item.status == "learning" else "[ ]"
                lines.append(f"- {marker} **{item.title}** ({item.status.replace('_', ' ').title()})")
                if item.description:
                    lines.append(f"  - {item.description}")
                if item.notes:
                    lines.append(f"  - *Notes*: {item.notes}")
            content = "\n".join(lines)

        ext = ".md" if format_type == "markdown" else f".{format_type}"
        full_filename = f"{filename}{ext}"

        store.exports[str(export_id)] = {
            "id": str(export_id),
            "source_type": source_type,
            "source_id": source_id,
            "format": format_type,
            "status": "completed",
            "content": content,
            "filename": full_filename,
            "created_at": now,
        }

        if db is not None:
            try:
                db_export = Export(
                    id=export_id,
                    workspace_id=workspace_id,
                    user_id=user_id,
                    source_type=source_type,
                    source_id=_to_uuid(source_id) or export_id,
                    format=format_type,
                    status="completed",
                    storage_path=full_filename,
                    created_at=now,
                )
                db.add(db_export)
                await db.commit()
            except Exception as e:
                logger.warning("Failed to persist export in DB: %s", e)

        return ExportResponse(
            id=str(export_id),
            source_type=source_type,
            source_id=source_id,
            format=format_type,
            status="completed",
            content=content,
            filename=full_filename,
            created_at=now,
        )
