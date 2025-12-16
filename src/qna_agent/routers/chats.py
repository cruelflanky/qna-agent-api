from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from qna_agent.database import get_db
from qna_agent.models.schemas import (
    ChatCreate,
    ChatListResponse,
    ChatResponse,
)
from qna_agent.services.chat import ChatService

router = APIRouter(prefix="/chats", tags=["chats"])


@router.post(
    "",
    response_model=ChatResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new chat session",
)
async def create_chat(
    body: ChatCreate = None,
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """Create a new chat session."""
    service = ChatService(db)
    title = body.title if body else None
    chat = await service.create_chat(title=title)
    return ChatResponse.model_validate(chat)


@router.get(
    "",
    response_model=ChatListResponse,
    summary="List all chat sessions",
)
async def list_chats(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: AsyncSession = Depends(get_db),
) -> ChatListResponse:
    """List all chat sessions with pagination."""
    service = ChatService(db)
    chats, total = await service.list_chats(limit=limit, offset=offset)
    return ChatListResponse(
        items=[ChatResponse.model_validate(c) for c in chats],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{chat_id}",
    response_model=ChatResponse,
    summary="Get chat session details",
)
async def get_chat(
    chat_id: str,
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """Get a specific chat session by ID."""
    service = ChatService(db)
    chat = await service.get_chat(chat_id)
    if chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )
    return ChatResponse.model_validate(chat)


@router.delete(
    "/{chat_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a chat session",
)
async def delete_chat(
    chat_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a chat session and all its messages."""
    service = ChatService(db)
    deleted = await service.delete_chat(chat_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )
