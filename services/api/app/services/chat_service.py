from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.errors import AppError, NotFoundError, ForbiddenError
from app.db.models import Conversation, Document, DocumentChunk, Message, MessageCitation, Project, Workspace
from app.db.session import get_session_factory
from app.rag.pipeline import AdvancedRAGPipeline, AdvancedRAGResult, BaselineRAGPipeline, BaselineRAGResult


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ChatService:
    """
    Coordinates baseline and advanced hybrid RAG execution with conversation and citation persistence.
    Enforces tenant boundaries and authorization.
    """

    def __init__(
        self,
        baseline_pipeline: Optional[BaselineRAGPipeline] = None,
        advanced_pipeline: Optional[AdvancedRAGPipeline] = None,
    ):
        self.baseline_pipeline = baseline_pipeline or BaselineRAGPipeline()
        self.advanced_pipeline = advanced_pipeline or AdvancedRAGPipeline()
        # Backward compatibility alias
        self.pipeline = self.advanced_pipeline if settings.RAG_RETRIEVAL_MODE == "advanced" else self.baseline_pipeline

    async def get_or_create_conversation(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        conversation_id: Optional[uuid.UUID] = None,
        title: Optional[str] = None,
    ) -> Conversation:
        if conversation_id:
            stmt = (
                select(Conversation)
                .where(
                    Conversation.id == conversation_id,
                    Conversation.workspace_id == workspace_id,
                    Conversation.project_id == project_id,
                )
            )
            res = await session.execute(stmt)
            conv = res.scalar_one_or_none()
            if not conv:
                raise NotFoundError(f"Conversation {conversation_id} not found in this project.")
            return conv

        # Create new conversation
        conv = Conversation(
            workspace_id=workspace_id,
            project_id=project_id,
            user_id=user_id,
            title=title or "New Conversation",
            status="active",
        )
        session.add(conv)
        await session.flush()
        return conv

    async def handle_chat_query(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        query: str,
        conversation_id: Optional[uuid.UUID] = None,
        top_k: int = settings.RAG_DEFAULT_TOP_K,
        document_ids: Optional[List[uuid.UUID]] = None,
        retrieval_mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes baseline or advanced hybrid RAG pipeline and persists messages & citations to PostgreSQL.
        """
        active_mode = (retrieval_mode or settings.RAG_RETRIEVAL_MODE or "advanced").lower().strip()

        session_factory = get_session_factory()
        async with session_factory() as session:
            # 1. Authorize project access
            proj_stmt = select(Project).where(
                Project.id == project_id,
                Project.workspace_id == workspace_id,
            )
            proj_res = await session.execute(proj_stmt)
            project = proj_res.scalar_one_or_none()
            if not project:
                raise ForbiddenError("You do not have access to this project workspace.")

            # 2. Retrieve or create conversation
            conv = await self.get_or_create_conversation(
                session=session,
                workspace_id=workspace_id,
                project_id=project_id,
                user_id=user_id,
                conversation_id=conversation_id,
                title=query[:40] if query else "New Chat",
            )

            # 3. Persist User Message
            user_msg = Message(
                conversation_id=conv.id,
                workspace_id=workspace_id,
                role="user",
                content=query.strip(),
                original_user_query=query.strip(),
            )
            session.add(user_msg)
            await session.flush()

            # 4. Execute Selected RAG Pipeline (Baseline or Advanced Hybrid)
            if active_mode == "baseline":
                rag_result = await self.baseline_pipeline.execute(
                    query=query.strip(),
                    workspace_id=workspace_id,
                    project_id=project_id,
                    top_k=top_k,
                    document_ids=document_ids,
                )
            else:
                rag_result = await self.advanced_pipeline.execute(
                    query=query.strip(),
                    workspace_id=workspace_id,
                    project_id=project_id,
                    dense_top_k=settings.RAG_DENSE_TOP_K,
                    lexical_top_k=settings.RAG_LEXICAL_TOP_K,
                    final_top_k=top_k or settings.RAG_RERANK_TOP_N,
                    document_ids=document_ids,
                )

            # 5. Persist Assistant Message
            assistant_msg = Message(
                conversation_id=conv.id,
                workspace_id=workspace_id,
                role="assistant",
                content=rag_result.answer,
                provider=rag_result.provider,
                model_id=rag_result.llm_model,
                token_usage=rag_result.token_usage,
                latency_ms=rag_result.total_latency_ms,
            )
            session.add(assistant_msg)
            await session.flush()

            # 6. Persist Citations with Provenance
            persisted_citations = []
            for order, cit in enumerate(rag_result.citations, start=1):
                valid_chunk_id = None
                matched_chunk = None
                if cit.chunk_id:
                    matched_chunk = await session.get(DocumentChunk, cit.chunk_id)
                    if matched_chunk:
                        valid_chunk_id = cit.chunk_id

                valid_doc_id = None
                if cit.document_id:
                    doc_rec = await session.get(Document, cit.document_id)
                    if doc_rec:
                        valid_doc_id = cit.document_id

                snapshot = {
                    "document_filename": cit.document_filename,
                    "page_start": cit.page_start,
                    "page_end": cit.page_end,
                    "slide_number": cit.slide_number,
                    "section_path": cit.section_path,
                    "similarity_score": cit.similarity_score,
                    "citation_label": cit.citation_label,
                    "snippet": cit.snippet,
                    "retrieval_mode": active_mode,
                }
                citation_record = MessageCitation(
                    message_id=assistant_msg.id,
                    chunk_id=valid_chunk_id,
                    document_id=valid_doc_id,
                    source_location_snapshot=snapshot,
                    citation_order=order,
                    validation_status="valid",
                )
                session.add(citation_record)
                persisted_citations.append({
                    "id": str(citation_record.id),
                    "document_id": str(cit.document_id),
                    "document_title": cit.document_filename,
                    "page_start": cit.page_start,
                    "page_end": cit.page_end,
                    "section_path": cit.section_path or "",
                    "snippet": cit.snippet,
                    "similarity_score": cit.similarity_score,
                    "citation_label": cit.citation_label,
                })

            conv.updated_at = utc_now()
            await session.commit()

            metrics = {
                "total_latency_ms": rag_result.total_latency_ms,
                "retrieval_latency_ms": rag_result.retrieval_latency_ms,
                "generation_latency_ms": rag_result.generation_latency_ms,
                "retrieved_chunks": len(rag_result.retrieved_chunks),
                "model": rag_result.llm_model,
                "embedding_model": rag_result.embedding_model,
                "retrieval_mode": getattr(rag_result, "retrieval_mode", active_mode),
                "dense_latency_ms": getattr(rag_result, "dense_latency_ms", 0),
                "lexical_latency_ms": getattr(rag_result, "lexical_latency_ms", 0),
                "fusion_latency_ms": getattr(rag_result, "fusion_latency_ms", 0),
                "rerank_latency_ms": getattr(rag_result, "rerank_latency_ms", 0),
                "dense_candidates": getattr(rag_result, "dense_candidates_count", 0),
                "lexical_candidates": getattr(rag_result, "lexical_candidates_count", 0),
                "fused_candidates": getattr(rag_result, "fused_candidates_count", 0),
            }

            return {
                "conversation_id": str(conv.id),
                "message": {
                    "id": str(assistant_msg.id),
                    "conversation_id": str(conv.id),
                    "role": "assistant",
                    "content": assistant_msg.content,
                    "citations": persisted_citations,
                    "created_at": assistant_msg.created_at.isoformat(),
                    "latency_ms": assistant_msg.latency_ms,
                    "model": assistant_msg.model_id,
                },
                "metrics": metrics,
            }

    async def list_conversations(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> List[Dict[str, Any]]:
        session_factory = get_session_factory()
        async with session_factory() as session:
            stmt = (
                select(Conversation)
                .where(
                    Conversation.workspace_id == workspace_id,
                    Conversation.project_id == project_id,
                )
                .order_by(Conversation.updated_at.desc())
            )
            res = await session.execute(stmt)
            conversations = res.scalars().all()
            return [
                {
                    "id": str(c.id),
                    "workspace_id": str(c.workspace_id),
                    "project_id": str(c.project_id),
                    "title": c.title,
                    "is_pinned": c.is_pinned,
                    "status": c.status,
                    "created_at": c.created_at.isoformat(),
                    "updated_at": c.updated_at.isoformat(),
                }
                for c in conversations
            ]

    async def get_conversation_messages(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        conversation_id: uuid.UUID,
    ) -> List[Dict[str, Any]]:
        session_factory = get_session_factory()
        async with session_factory() as session:
            # Check conversation exists
            conv_stmt = select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.workspace_id == workspace_id,
                Conversation.project_id == project_id,
            )
            c_res = await session.execute(conv_stmt)
            if not c_res.scalar_one_or_none():
                raise NotFoundError("Conversation not found.")

            stmt = (
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .options(selectinload(Message.citations))
                .order_by(Message.created_at.asc())
            )
            res = await session.execute(stmt)
            messages = res.scalars().all()

            results = []
            for m in messages:
                cits = [
                    {
                        "id": str(c.id),
                        "document_id": str(c.document_id) if c.document_id else "",
                        "document_title": c.source_location_snapshot.get("document_filename", "Document"),
                        "page_start": c.source_location_snapshot.get("page_start"),
                        "page_end": c.source_location_snapshot.get("page_end"),
                        "section_path": c.source_location_snapshot.get("section_path", ""),
                        "snippet": c.source_location_snapshot.get("snippet", ""),
                        "similarity_score": c.source_location_snapshot.get("similarity_score", 0.0),
                        "citation_label": c.source_location_snapshot.get("citation_label", ""),
                    }
                    for c in m.citations
                ]
                results.append({
                    "id": str(m.id),
                    "conversation_id": str(m.conversation_id),
                    "role": m.role,
                    "content": m.content,
                    "citations": cits,
                    "created_at": m.created_at.isoformat(),
                    "latency_ms": m.latency_ms,
                    "model": m.model_id,
                })
            return results
