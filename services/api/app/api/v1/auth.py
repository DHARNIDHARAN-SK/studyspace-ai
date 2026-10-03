from fastapi import APIRouter, Depends
from app.core.auth import AuthenticatedUser, get_current_user
from app.db.repository import Repository
from app.schemas.auth import ProvisionRequest, UserProfileResponse

router = APIRouter(prefix="", tags=["Auth & Profile"])


@router.get("/me", response_model=UserProfileResponse)
async def get_current_profile(
    current_user: AuthenticatedUser = Depends(get_current_user)
) -> UserProfileResponse:
    profile = Repository.get_profile(current_user.id)
    return UserProfileResponse(
        id=current_user.id,
        email=current_user.email,
        display_name=profile.get("display_name") if profile else None,
        avatar_url=profile.get("avatar_url") if profile else None,
        workspace_id=current_user.workspace_id,
        workspace_name=current_user.workspace_name,
        created_at=profile["created_at"] if profile else None,
        updated_at=profile["updated_at"] if profile else None,
    )


@router.post("/auth/provision", response_model=UserProfileResponse)
async def provision_user(
    body: ProvisionRequest,
    current_user: AuthenticatedUser = Depends(get_current_user)
) -> UserProfileResponse:
    profile = Repository.upsert_profile(
        user_id=current_user.id,
        display_name=body.display_name,
        avatar_url=body.avatar_url,
    )
    return UserProfileResponse(
        id=current_user.id,
        email=current_user.email,
        display_name=profile["display_name"],
        avatar_url=profile["avatar_url"],
        workspace_id=current_user.workspace_id,
        workspace_name=current_user.workspace_name,
        created_at=profile["created_at"],
        updated_at=profile["updated_at"],
    )
