
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from qna_agent.models.db import Chat, Message


class ChatService:
    """Service for chat operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_chat(self, title: str | None = None) -> Chat:
        """Create a new chat session."""
        chat = Chat(title=title)
        self.session.add(chat)
        await self.session.flush()
        await self.session.refresh(chat)
        return chat

    async def get_chat(self, chat_id: str) -> Chat | None:
        """Get chat by ID."""
        result = await self.session.execute(
            select(Chat).where(Chat.id == chat_id)
        )
        return result.scalar_one_or_none()

    async def list_chats(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Chat], int]:
        """List chats with pagination."""
        # Get total count
        count_result = await self.session.execute(
            select(func.count()).select_from(Chat)
        )
        total = count_result.scalar_one()

        # Get paginated results
        result = await self.session.execute(
            select(Chat)
            .order_by(Chat.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        chats = list(result.scalars().all())

        return chats, total

    async def delete_chat(self, chat_id: str) -> bool:
        """Delete chat by ID. Returns True if deleted."""
        chat = await self.get_chat(chat_id)
        if chat is None:
            return False

        await self.session.delete(chat)
        return True

    async def update_chat_timestamp(self, chat_id: str) -> None:
        """Update chat's updated_at timestamp."""
        chat = await self.get_chat(chat_id)
        if chat:
            # SQLAlchemy will auto-update via onupdate
            await self.session.flush()


class MessageService:
    """Service for message operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_message(
        self,
        chat_id: str,
        role: str,
        content: str | None = None,
        tool_calls: str | None = None,
        tool_call_id: str | None = None,
    ) -> Message:
        """Create a new message."""
        message = Message(
            chat_id=chat_id,
            role=role,
            content=content,
            tool_calls=tool_calls,
            tool_call_id=tool_call_id,
        )
        self.session.add(message)
        await self.session.flush()
        await self.session.refresh(message)
        return message

    async def get_messages(
        self,
        chat_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Message], int]:
        """Get messages for a chat with pagination."""
        # Get total count
        count_result = await self.session.execute(
            select(func.count())
            .select_from(Message)
            .where(Message.chat_id == chat_id)
        )
        total = count_result.scalar_one()

        # Get paginated results (oldest first for conversation order)
        result = await self.session.execute(
            select(Message)
            .where(Message.chat_id == chat_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        messages = list(result.scalars().all())

        return messages, total

    async def get_all_messages(self, chat_id: str) -> list[Message]:
        """Get all messages for a chat (for LLM context)."""
        result = await self.session.execute(
            select(Message)
            .where(Message.chat_id == chat_id)
            .order_by(Message.created_at.asc())
        )
        return list(result.scalars().all())
