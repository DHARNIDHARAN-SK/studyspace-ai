from datetime import datetime, timezone
import uuid
from typing import List, Optional, Tuple
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models import Document, DocumentChunk, IngestionJob, Profile, Project, Workspace
from app.db.repository import Repository
from app.db.session import get_session_factory


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def ensure_workspace_hierarchy(
    session: AsyncSession,
    user_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> Workspace:
    """
    Ensures that Profile and Workspace rows exist in the PostgreSQL database,
    satisfying foreign key constraints.
    """
    # 1. Check or insert profile
    profile = await session.get(Profile, user_id)
    if not profile:
        # Also ensure auth.users record exists if foreign key exists in schema
        try:
            async with session.begin_nested():
                await session.execute(
                    text(
                        "INSERT INTO auth.users (id, email) VALUES (:id, :email) ON CONFLICT (id) DO NOTHING"
                    ),
                    {"id": user_id, "email": f"user-{user_id}@studyspace.ai"},
                )
        except Exception:
            pass  # Schema might not have auth schema in sqlite/mock test environments

        profile = Profile(id=user_id, display_name="Student")
        session.add(profile)
        await session.flush()

    # 2. Check or insert workspace
    workspace = await session.get(Workspace, workspace_id)
    if not workspace:
        existing_ws_stmt = select(Workspace).where(Workspace.owner_user_id == user_id)
        existing_ws = (await session.execute(existing_ws_stmt)).scalars().first()
        if existing_ws:
            workspace = existing_ws
        else:
            workspace = Workspace(
                id=workspace_id,
                owner_user_id=user_id,
                name="Personal Workspace",
            )
            session.add(workspace)
            await session.flush()

    return workspace


async def ensure_tenant_hierarchy(
    session: AsyncSession,
    user_id: uuid.UUID,
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
) -> Project:
    """
    Ensures that Profile, Workspace, and Project rows exist in the PostgreSQL database,
    satisfying foreign key constraints and verifying workspace-project isolation.
    """
    workspace = await ensure_workspace_hierarchy(session, user_id, workspace_id)

    # 3. Check or insert project
    project = await session.get(Project, project_id)
    if not project:
        # Check if project exists in in-memory repository to preserve name/subject
        repo_proj = None
        try:
            repo_proj = Repository.get_project(str(workspace_id), str(project_id))
        except Exception:
            pass

        project_name = repo_proj["name"] if repo_proj else "Course Project"
        project_subject = repo_proj.get("subject") if repo_proj else None

        project = Project(
            id=project_id,
            workspace_id=workspace.id,
            name=project_name,
            subject=project_subject,
        )
        session.add(project)
        await session.flush()
    else:
        # Verify project belongs to workspace or user
        if project.workspace_id != workspace_id and project.workspace_id != workspace.id:
            proj_ws = await session.get(Workspace, project.workspace_id)
            if not (proj_ws and proj_ws.owner_user_id == user_id):
                raise AppError(
                    code="PROJECT_WORKSPACE_MISMATCH",
                    message="Project does not belong to the authorized workspace.",
                    status_code=403,
                )

    return project


async def get_project_document(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    document_id: uuid.UUID,
) -> Document:
    """Retrieves a document enforcing project and workspace tenant isolation."""
    stmt = (
        select(Document)
        .where(
            Document.id == document_id,
            Document.project_id == project_id,
            Document.workspace_id == workspace_id,
            Document.deleted_at.is_(None),
        )
    )
    result = await session.execute(stmt)
    document = result.scalar_one_or_none()
    if not document:
        raise AppError(
            code="DOCUMENT_NOT_FOUND",
            message="Document not found or access denied.",
            status_code=404,
            action="Verify the document ID and project scope.",
        )
    return document


async def list_project_documents(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
) -> List[Tuple[Document, int]]:
    """
    Lists all non-deleted documents for a project along with their chunk counts.
    Returns list of (Document, chunk_count) tuples.
    """
    stmt = (
        select(
            Document,
            func.count(DocumentChunk.id).label("chunk_count"),
        )
        .outerjoin(
            DocumentChunk,
            (DocumentChunk.document_id == Document.id)
            & (DocumentChunk.document_version == Document.document_version),
        )
        .where(
            Document.project_id == project_id,
            Document.workspace_id == workspace_id,
            Document.deleted_at.is_(None),
        )
        .group_by(Document.id)
        .order_by(Document.created_at.desc())
    )
    result = await session.execute(stmt)
    return result.all()
