from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from app.core.auth import AuthenticatedUser, get_current_user
from app.db.repository import Repository
from app.schemas.projects import ProjectCreate, ProjectListResponse, ProjectResponse, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> ProjectResponse:
    project = Repository.create_project(
        workspace_id=current_user.workspace_id,
        name=body.name,
        description=body.description,
        subject=body.subject,
    )
    return ProjectResponse(**project)


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    include_archived: bool = Query(False, description="Whether to include archived projects"),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> ProjectListResponse:
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
) -> ProjectResponse:
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
) -> ProjectResponse:
    project = Repository.update_project(
        workspace_id=current_user.workspace_id,
        project_id=project_id,
        name=body.name,
        description=body.description,
        subject=body.subject,
        is_archived=body.is_archived,
    )
    return ProjectResponse(**project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    Repository.delete_project(
        workspace_id=current_user.workspace_id,
        project_id=project_id,
    )
    return None
