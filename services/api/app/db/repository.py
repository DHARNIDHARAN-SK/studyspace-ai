from datetime import datetime, timezone
import uuid
from typing import Dict, List, Optional
from app.core.errors import AppError


class MemoryStore:
    """In-memory thread-safe store for development and fast automated testing."""
    def __init__(self):
        self.profiles: Dict[str, dict] = {}
        self.workspaces: Dict[str, dict] = {}
        self.projects: Dict[str, dict] = {}

    def clear(self):
        self.profiles.clear( )
        self.workspaces.clear()
        self.projects.clear()


# Global store instance
store = MemoryStore()


class Repository:
    """Data repository interface enforcing workspace-scoped multi-tenancy."""

    # --------------------------------------------------------------------------
    # Profiles & Workspaces (User provisioning)
    # --------------------------------------------------------------------------
    @staticmethod
    def get_profile(user_id: str) -> Optional[dict]:
        return store.profiles.get(user_id)

    @staticmethod
    def upsert_profile(user_id: str, display_name: Optional[str] = None, avatar_url: Optional[str] = None) -> dict:
        now = datetime.now(timezone.utc)
        existing = store.profiles.get(user_id)
        if existing:
            if display_name is not None:
                existing["display_name"] = display_name
            if avatar_url is not None:
                existing["avatar_url"] = avatar_url
            existing["updated_at"] = now
            return existing

        profile = {
            "id": user_id,
            "display_name": display_name or "Student",
            "avatar_url": avatar_url,
            "created_at": now,
            "updated_at": now,
        }
        store.profiles[user_id] = profile
        return profile

    @staticmethod
    def get_or_create_workspace(user_id: str, default_name: str = "Personal Workspace") -> dict:
        # Check if user already owns a workspace
        for ws in store.workspaces.values():
            if ws["owner_user_id"] == user_id:
                return ws

        now = datetime.now(timezone.utc)
        ws_id = str(uuid.uuid4())
        workspace = {
            "id": ws_id,
            "owner_user_id": user_id,
            "name": default_name,
            "created_at": now,
            "updated_at": now,
        }
        store.workspaces[ws_id] = workspace
        return workspace

    @staticmethod
    def get_workspace_by_id(workspace_id: str) -> Optional[dict]:
        return store.workspaces.get(workspace_id)

    # --------------------------------------------------------------------------
    # Projects (Strictly scoped by workspace_id)
    # --------------------------------------------------------------------------
    @staticmethod
    def create_project(workspace_id: str, name: str, description: Optional[str] = None, subject: Optional[str] = None) -> dict:
        now = datetime.now(timezone.utc)
        project_id = str(uuid.uuid4())
        project = {
            "id": project_id,
            "workspace_id": workspace_id,
            "name": name,
            "description": description,
            "subject": subject,
            "created_at": now,
            "updated_at": now,
            "archived_at": None,
        }
        store.projects[project_id] = project
        return project

    @staticmethod
    def list_projects(workspace_id: str, include_archived: bool = False) -> List[dict]:
        results = []
        for p in store.projects.values():
            if p["workspace_id"] == workspace_id:
                if not include_archived and p["archived_at"] is not None:
                    continue
                results.append(p)
        # Sort by updated_at descending
        results.sort(key=lambda x: x["updated_at"], reverse=True)
        return results

    @staticmethod
    def get_project(workspace_id: str, project_id: str) -> dict:
        project = store.projects.get(project_id)
        if not project or project["workspace_id"] != workspace_id:
            raise AppError(
                code="PROJECT_NOT_FOUND",
                message="The requested project was not found in your workspace.",
                status_code=404,
                action="Verify the project ID or ensure you have access to this workspace.",
            )
        return project

    @staticmethod
    def update_project(
        workspace_id: str,
        project_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        subject: Optional[str] = None,
        is_archived: Optional[bool] = None,
    ) -> dict:
        project = Repository.get_project(workspace_id, project_id)
        now = datetime.now(timezone.utc)

        if name is not None:
            project["name"] = name
        if description is not None:
            project["description"] = description
        if subject is not None:
            project["subject"] = subject
        if is_archived is not None:
            project["archived_at"] = now if is_archived else None

        project["updated_at"] = now
        return project

    @staticmethod
    def delete_project(workspace_id: str, project_id: str) -> dict:
        project = Repository.get_project(workspace_id, project_id)
        del store.projects[project_id]
        return project
