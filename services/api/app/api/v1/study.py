from typing import Any, Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.errors import AppError
from app.db.session import get_db_optional
from app.schemas.study import (
    ExportRequest,
    ExportResponse,
    QuizAttemptResultResponse,
    QuizGenerateRequest,
    QuizListResponse,
    QuizResponse,
    QuizSubmitRequest,
    RevisionItemCreate,
    RevisionItemResponse,
    RevisionItemUpdate,
    RevisionLinkCreate,
    RevisionLinkResponse,
    RevisionListResponse,
    StudyGuideGenerateRequest,
    StudyGuideListResponse,
    StudyGuideResponse,
)
from app.services.study_service import StudyService

router = APIRouter(prefix="/projects/{project_id}", tags=["Student Study Features"])
study_service = StudyService()


def _parse_uuids(current_user: AuthenticatedUser, project_id: str) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    try:
        user_uuid = uuid.UUID(current_user.id)
    except ValueError:
        user_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"user-{current_user.id}")

    try:
        ws_uuid = uuid.UUID(current_user.workspace_id)
    except ValueError:
        ws_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"workspace-{current_user.workspace_id}")

    try:
        proj_uuid = uuid.UUID(project_id)
    except ValueError:
        proj_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"project-{project_id}")

    return user_uuid, ws_uuid, proj_uuid


# ==============================================================================
# 1. Revision Checklist
# ==============================================================================
@router.post("/revision", response_model=RevisionItemResponse, status_code=status.HTTP_201_CREATED)
async def create_revision_item(
    project_id: str,
    body: RevisionItemCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db_optional),
) -> RevisionItemResponse:
    user_uuid, ws_uuid, proj_uuid = _parse_uuids(current_user, project_id)
    return await study_service.create_revision_item(
        user_id=user_uuid,
        workspace_id=ws_uuid,
        project_id=proj_uuid,
        data=body,
        db=db,
    )


@router.get("/revision", response_model=RevisionListResponse)
async def list_revision_items(
    project_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db_optional),
) -> RevisionListResponse:
    user_uuid, ws_uuid, proj_uuid = _parse_uuids(current_user, project_id)
    return await study_service.list_revision_items(
        user_id=user_uuid,
        workspace_id=ws_uuid,
        project_id=proj_uuid,
        db=db,
    )


@router.patch("/revision/{item_id}", response_model=RevisionItemResponse)
async def update_revision_item(
    project_id: str,
    item_id: str,
    body: RevisionItemUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db_optional),
) -> RevisionItemResponse:
    user_uuid, ws_uuid, proj_uuid = _parse_uuids(current_user, project_id)
    try:
        item_uuid = uuid.UUID(item_id)
    except ValueError:
        item_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"rev-{item_id}")

    return await study_service.update_revision_item(
        user_id=user_uuid,
        workspace_id=ws_uuid,
        project_id=proj_uuid,
        item_id=item_uuid,
        data=body,
        db=db,
    )


@router.delete("/revision/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_revision_item(
    project_id: str,
    item_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db_optional),
):
    user_uuid, ws_uuid, proj_uuid = _parse_uuids(current_user, project_id)
    try:
        item_uuid = uuid.UUID(item_id)
    except ValueError:
        item_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"rev-{item_id}")

    await study_service.delete_revision_item(
        user_id=user_uuid,
        workspace_id=ws_uuid,
        project_id=proj_uuid,
        item_id=item_uuid,
        db=db,
    )
    return None


@router.post("/revision/{item_id}/links", response_model=RevisionLinkResponse, status_code=status.HTTP_201_CREATED)
async def add_revision_link(
    project_id: str,
    item_id: str,
    body: RevisionLinkCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db_optional),
) -> RevisionLinkResponse:
    user_uuid, ws_uuid, proj_uuid = _parse_uuids(current_user, project_id)
    try:
        item_uuid = uuid.UUID(item_id)
    except ValueError:
        item_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"rev-{item_id}")

    return await study_service.add_revision_link(
        user_id=user_uuid,
        workspace_id=ws_uuid,
        project_id=proj_uuid,
        item_id=item_uuid,
        data=body,
        db=db,
    )


# ==============================================================================
# 2. Study Guides
# ==============================================================================
@router.post("/guides", response_model=StudyGuideResponse, status_code=status.HTTP_201_CREATED)
async def generate_study_guide(
    project_id: str,
    body: StudyGuideGenerateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db_optional),
) -> StudyGuideResponse:
    user_uuid, ws_uuid, proj_uuid = _parse_uuids(current_user, project_id)
    return await study_service.generate_study_guide(
        user_id=user_uuid,
        workspace_id=ws_uuid,
        project_id=proj_uuid,
        topic=body.topic,
        guide_type=body.guide_type,
        focus_areas=body.focus_areas,
        db=db,
    )


@router.get("/guides", response_model=StudyGuideListResponse)
async def list_study_guides(
    project_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db_optional),
) -> StudyGuideListResponse:
    user_uuid, ws_uuid, proj_uuid = _parse_uuids(current_user, project_id)
    return await study_service.list_study_guides(
        user_id=user_uuid,
        workspace_id=ws_uuid,
        project_id=proj_uuid,
        db=db,
    )


@router.get("/guides/{guide_id}", response_model=StudyGuideResponse)
async def get_study_guide(
    project_id: str,
    guide_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db_optional),
) -> StudyGuideResponse:
    user_uuid, ws_uuid, proj_uuid = _parse_uuids(current_user, project_id)
    try:
        guide_uuid = uuid.UUID(guide_id)
    except ValueError:
        guide_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"guide-{guide_id}")

    return await study_service.get_study_guide(
        user_id=user_uuid,
        workspace_id=ws_uuid,
        project_id=proj_uuid,
        guide_id=guide_uuid,
        db=db,
    )


# ==============================================================================
# 3. Quizzes
# ==============================================================================
@router.post("/quizzes", response_model=QuizResponse, status_code=status.HTTP_201_CREATED)
async def generate_quiz(
    project_id: str,
    body: QuizGenerateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db_optional),
) -> QuizResponse:
    user_uuid, ws_uuid, proj_uuid = _parse_uuids(current_user, project_id)
    return await study_service.generate_quiz(
        user_id=user_uuid,
        workspace_id=ws_uuid,
        project_id=proj_uuid,
        title=body.title,
        topic=body.topic,
        num_questions=body.num_questions,
        difficulty=body.difficulty,
        question_types=body.question_types,
        db=db,
    )


@router.get("/quizzes", response_model=QuizListResponse)
async def list_quizzes(
    project_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db_optional),
) -> QuizListResponse:
    user_uuid, ws_uuid, proj_uuid = _parse_uuids(current_user, project_id)
    return await study_service.list_quizzes(
        user_id=user_uuid,
        workspace_id=ws_uuid,
        project_id=proj_uuid,
        db=db,
    )


@router.get("/quizzes/{quiz_id}", response_model=QuizResponse)
async def get_quiz(
    project_id: str,
    quiz_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db_optional),
) -> QuizResponse:
    user_uuid, ws_uuid, proj_uuid = _parse_uuids(current_user, project_id)
    try:
        quiz_uuid = uuid.UUID(quiz_id)
    except ValueError:
        quiz_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"quiz-{quiz_id}")

    return await study_service.get_quiz(
        user_id=user_uuid,
        workspace_id=ws_uuid,
        project_id=proj_uuid,
        quiz_id=quiz_uuid,
        include_answers=False,
        db=db,
    )


@router.post("/quizzes/{quiz_id}/attempt", response_model=QuizAttemptResultResponse)
async def submit_quiz_attempt(
    project_id: str,
    quiz_id: str,
    body: QuizSubmitRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db_optional),
) -> QuizAttemptResultResponse:
    user_uuid, ws_uuid, proj_uuid = _parse_uuids(current_user, project_id)
    try:
        quiz_uuid = uuid.UUID(quiz_id)
    except ValueError:
        quiz_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"quiz-{quiz_id}")

    return await study_service.submit_quiz_attempt(
        user_id=user_uuid,
        workspace_id=ws_uuid,
        project_id=proj_uuid,
        quiz_id=quiz_uuid,
        responses=body.responses,
        db=db,
    )


# ==============================================================================
# 4. Export
# ==============================================================================
@router.post("/export", response_model=ExportResponse)
async def export_project_content(
    project_id: str,
    body: ExportRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db_optional),
) -> ExportResponse:
    user_uuid, ws_uuid, proj_uuid = _parse_uuids(current_user, project_id)
    return await study_service.export_content(
        user_id=user_uuid,
        workspace_id=ws_uuid,
        project_id=proj_uuid,
        source_type=body.source_type,
        source_id=body.source_id,
        format_type=body.format,
        db=db,
    )
