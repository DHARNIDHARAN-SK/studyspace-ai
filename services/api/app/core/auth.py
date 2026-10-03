from typing import Optional
from fastapi import Depends, Header
import jwt
from pydantic import BaseModel

from app.core.config import settings
from app.core.errors import AppError
from app.db.repository import Repository

# Development fallback secret for local test tokens
DEV_TEST_JWT_SECRET = "development-secret-for-local-testing-only"


class AuthenticatedUser(BaseModel):
    id: str
    email: Optional[str] = None
    workspace_id: str
    workspace_name: str


def decode_jwt_token(token: str) -> dict:
    """Decodes and validates a Supabase or local JWT token."""
    # Attempt verification using SUPABASE_JWT_SECRET if configured
    if settings.SUPABASE_JWT_SECRET:
        try:
            return jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_aud": False}
            )
        except jwt.PyJWTError as e:
            raise AppError(
                code="INVALID_TOKEN",
                message="The provided authentication token is invalid or has expired.",
                status_code=401,
                action="Please sign in again to obtain a fresh access token.",
                details={"reason": str(e)}
            )

    # In development / testing environments without remote secret
    try:
        # First attempt with dev secret
        return jwt.decode(
            token,
            DEV_TEST_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False}
        )
    except jwt.PyJWTError:
        # Fallback: unverified claims inspection strictly in development mode
        if settings.APP_ENV in ("development", "test"):
            try:
                return jwt.decode(token, options={"verify_signature": False})
            except Exception as e:
                raise AppError(
                    code="INVALID_TOKEN",
                    message="Malformed authentication token.",
                    status_code=401,
                    action="Provide a valid JWT token.",
                    details={"reason": str(e)}
                )
        raise AppError(
            code="INVALID_TOKEN",
            message="The provided authentication token could not be verified.",
            status_code=401,
            action="Please sign in again."
        )


async def get_current_user(authorization: Optional[str] = Header(None)) -> AuthenticatedUser:
    """FastAPI dependency to extract and authorize the authenticated user and workspace."""
    if not authorization:
        raise AppError(
            code="UNAUTHORIZED",
            message="Authentication credentials are required.",
            status_code=401,
            action="Include a valid Bearer token in the Authorization header."
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AppError(
            code="MALFORMED_AUTHORIZATION_HEADER",
            message="Authorization header must follow format: Bearer <token>",
            status_code=401,
            action="Format your header as 'Authorization: Bearer <token>'."
        )

    token = parts[1]
    payload = decode_jwt_token(token)

    user_id = payload.get("sub")
    if not user_id:
        raise AppError(
            code="INVALID_TOKEN_CLAIMS",
            message="Token does not contain a valid user identity claim (sub).",
            status_code=401
        )

    email = payload.get("email")

    # Ensure profile and default personal workspace are provisioned
    Repository.upsert_profile(user_id=user_id, display_name=payload.get("user_metadata", {}).get("full_name"))
    workspace = Repository.get_or_create_workspace(user_id=user_id)

    return AuthenticatedUser(
        id=user_id,
        email=email,
        workspace_id=workspace["id"],
        workspace_name=workspace["name"],
    )
