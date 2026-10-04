from datetime import datetime, timezone
from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.errors import AppError
from app.core.logging import logger
from app.db.models import Profile, Project, Workspace
from app.db.repository import Repository, store
from app.db.session import get_db_optional
from app.schemas.projects import ProjectCreate, ProjectListResponse, ProjectResponse, ProjectUpdate

from app.db.documents import ensure_tenant_hierarchy

router = APIRouter(prefix="/projects", tags=["Projects"])


def _to_uuid(val: str) -> Optional[uuid.UUID]:
    try:
        return uuid.UUID(str(val))
    except (ValueError, AttributeError, TypeError):
        try:
            return uuid.uuid5(uuid.NAMESPACE_DNS, str(val))
        except Exception:
            return None


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db_optional),
) -> ProjectResponse:
    project = Repository.create_project(
        workspace_id=current_user.workspace_id,
        name=body.name,
        description=body.description,
        subject=body.subject,
    )

    if db is not None:
        user_uuid = _to_uuid(current_user.id)
        ws_uuid = _to_uuid(current_user.workspace_id)
        proj_uuid = _to_uuid(project["id"])

        if user_uuid and ws_uuid and proj_uuid:
            try:
                await ensure_tenant_hierarchy(db, user_uuid, ws_uuid, proj_uuid)
                await db.commit()
            except Exception as e:
                logger.warning("Failed to sync created project to database: %s", e)
                try:
                    await db.rollback()
                except Exception:
                    pass

    return ProjectResponse(**project)


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    include_archived: bool = Query(False, description="Whether to include archived projects"),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db_optional),
) -> ProjectListResponse:
    if db is not None:
        user_uuid = _to_uuid(current_user.id)
        if user_uuid:
            try:
                stmt = (
                    select(Project)
                    .join(Workspace, Project.workspace_id == Workspace.id)
                    .where(Workspace.owner_user_id == user_uuid)
                )
                if not include_archived:
                    stmt = stmt.where(Project.archived_at.is_(None))
                res = await db.execute(stmt)
                db_projects = res.scalars().all()
                for p in db_projects:
                    p_id = str(p.id)
                    if p_id not in store.projects:
                        store.projects[p_id] = {
                            "id": p_id,
                            "workspace_id": str(p.workspace_id),
                            "name": p.name,
                            "description": p.description,
                            "subject": p.subject,
                            "created_at": p.created_at,
                            "updated_at": p.updated_at,
                            "archived_at": p.archived_at,
                        }
            except Exception as e:
                logger.warning("Failed to load projects from database: %s", e)

    projects = Repository.list_projects(
        workspace_id=current_user.workspace_id,
        include_archived=include_archived,
    )
    return ProjectListResponse(
        projects=[ProjectResponse(**p) for p in projects],
        total=len(projects),
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db_optional),
) -> ProjectResponse:
    if db is not None and project_id not in store.projects:
        proj_uuid = _to_uuid(project_id)
        user_uuid = _to_uuid(current_user.id)
        if proj_uuid and user_uuid:
            try:
                stmt = (
                    select(Project)
                    .join(Workspace, Project.workspace_id == Workspace.id)
                    .where(Project.id == proj_uuid, Workspace.owner_user_id == user_uuid)
                )
                res = await db.execute(stmt)
                p = res.scalars().first()
                if p:
                    store.projects[project_id] = {
                        "id": str(p.id),
                        "workspace_id": str(p.workspace_id),
                        "name": p.name,
                        "description": p.description,
                        "subject": p.subject,
                        "created_at": p.created_at,
                        "updated_at": p.updated_at,
                        "archived_at": p.archived_at,
                    }
            except Exception as e:
                logger.warning("Failed to get project from database: %s", e)

    project = Repository.get_project(
        workspace_id=current_user.workspace_id,
        project_id=project_id,
    )
    return ProjectResponse(**project)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    body: ProjectUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db_optional),
) -> ProjectResponse:
    project = Repository.update_project(
        workspace_id=current_user.workspace_id,
        project_id=project_id,
        name=body.name,
        description=body.description,
        subject=body.subject,
        is_archived=body.is_archived,
    )

    if db is not None:
        proj_uuid = _to_uuid(project_id)
        user_uuid = _to_uuid(current_user.id)
        if proj_uuid and user_uuid:
            try:
                stmt = (
                    select(Project)
                    .join(Workspace, Project.workspace_id == Workspace.id)
                    .where(Project.id == proj_uuid, Workspace.owner_user_id == user_uuid)
                )
                res = await db.execute(stmt)
                p = res.scalars().first()
                if p:
                    if body.name is not None:
                        p.name = body.name
                    if body.description is not None:
                        p.description = body.description
                    if body.subject is not None:
                        p.subject = body.subject
                    if body.is_archived is not None:
                        p.archived_at = datetime.now(timezone.utc) if body.is_archived else None
                    await db.commit()
            except Exception as e:
                logger.warning("Failed to update project in database: %s", e)

    return ProjectResponse(**project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db_optional),
):
    Repository.delete_project(
        workspace_id=current_user.workspace_id,
        project_id=project_id,
    )

    if db is not None:
        proj_uuid = _to_uuid(project_id)
        user_uuid = _to_uuid(current_user.id)
        if proj_uuid and user_uuid:
            try:
                stmt = (
                    select(Project)
                    .join(Workspace, Project.workspace_id == Workspace.id)
                    .where(Project.id == proj_uuid, Workspace.owner_user_id == user_uuid)
                )
                res = await db.execute(stmt)
                p = res.scalars().first()
                if p:
                    await db.delete(p)
                    await db.commit()
            except Exception as e:
                logger.warning("Failed to delete project in database: %s", e)

    return None


