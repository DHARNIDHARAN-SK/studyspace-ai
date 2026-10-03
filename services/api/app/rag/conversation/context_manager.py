from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.db.models import Message


@dataclass
class ConversationTurn:
    role: str
    content: str
    created_at: Optional[datetime] = None


class ConversationContextManager:
    """
    Manages bounded retrieval and formatting of conversation history for
    query rewriting and conversational generation.
    Enforces strict chronological ordering and tenant isolation.
    """

    def __init__(self, history_limit: int = settings.RAG_CONVERSATION_HISTORY_LIMIT):
        self.history_limit = history_limit

    async def get_recent_history(
        self,
        session: AsyncSession,
        conversation_id: Optional[uuid.UUID],
        workspace_id: uuid.UUID,
        limit: Optional[int] = None,
    ) -> List[ConversationTurn]:
        """
        Retrieves the most recent N messages for a conversation, ordered chronologically (oldest to newest).
        """
        if not conversation_id:
            return []

        fetch_limit = limit or self.history_limit
        if fetch_limit <= 0:
            return []

        # Subquery to fetch the last N messages by created_at DESC
        subq = (
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.workspace_id == workspace_id,
            )
            .order_by(Message.created_at.desc())
            .limit(fetch_limit)
            .subquery()
        )

        # Outer query to sort them ASC (chronological flow)
        aliased_msg = select(subq).order_by(subq.c.created_at.asc())
        result = await session.execute(aliased_msg)
        rows = result.fetchall()

        turns = []
        for row in rows:
            turns.append(
                ConversationTurn(
                    role=row.role,
                    content=row.content or "",
                    created_at=row.created_at,
                )
            )

        logger.debug(
            "Retrieved %d conversation turns for conversation %s (limit=%d)",
            len(turns),
            conversation_id,
            fetch_limit,
        )
        return turns

    @staticmethod
    def format_history_for_rewrite(history: List[ConversationTurn]) -> str:
        """
        Formats conversation history concisely for the query rewriter prompt.
        """
        if not history:
            return "No previous conversation."

        formatted_lines = []
        for turn in history:
            role_label = "User" if turn.role.lower() == "user" else "Assistant"
            clean_content = turn.content.strip().replace("\n", " ")
            formatted_lines.append(f"{role_label}: {clean_content}")

        return "\n".join(formatted_lines)

    @staticmethod
    def format_history_for_prompt(history: List[ConversationTurn]) -> str:
        """
        Formats conversation history for LLM generation context.
        """
        if not history:
            return ""

        formatted_lines = ["[Conversation History]"]
        for turn in history:
            role_label = "Student" if turn.role.lower() == "user" else "Assistant"
            formatted_lines.append(f"{role_label}: {turn.content.strip()}")
        formatted_lines.append("[End Conversation History]")

        return "\n".join(formatted_lines)
