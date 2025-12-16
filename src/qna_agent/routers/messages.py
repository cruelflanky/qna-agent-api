import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from qna_agent.database import get_db
from qna_agent.models.schemas import (
    MessageCreate,
    MessageListResponse,
    MessageResponse,
    SendMessageResponse,
)
from qna_agent.routers.events import broadcast_message, broadcast_typing
from qna_agent.services.agent import AgentService
from qna_agent.services.chat import ChatService, MessageService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chats/{chat_id}/messages", tags=["messages"])


def _convert_message(msg) -> MessageResponse:
    """Convert DB message to response schema with tool_calls parsing."""
    tool_calls = None
    if msg.tool_calls:
        try:
            tool_calls = json.loads(msg.tool_calls)
        except json.JSONDecodeError:
            pass

    return MessageResponse(
        id=msg.id,
        chat_id=msg.chat_id,
        role=msg.role,
        content=msg.content,
        tool_calls=tool_calls,
        tool_call_id=msg.tool_call_id,
        created_at=msg.created_at,
    )


@router.get(
    "",
    response_model=MessageListResponse,
    summary="Get message history for a chat",
)
async def get_messages(
    chat_id: str,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: AsyncSession = Depends(get_db),
) -> MessageListResponse:
    """Get all messages for a chat session with pagination."""
    # Verify chat exists
    chat_service = ChatService(db)
    chat = await chat_service.get_chat(chat_id)
    if chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )

    message_service = MessageService(db)
    messages, total = await message_service.get_messages(
        chat_id=chat_id,
        limit=limit,
        offset=offset,
    )

    return MessageListResponse(
        items=[_convert_message(m) for m in messages],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    response_model=SendMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a message and get AI response",
)
async def send_message(
    chat_id: str,
    body: MessageCreate,
    db: AsyncSession = Depends(get_db),
) -> SendMessageResponse:
    """Send a user message and receive an AI-generated response."""
    # Verify chat exists
    chat_service = ChatService(db)
    chat = await chat_service.get_chat(chat_id)
    if chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )

    # Broadcast typing indicator
    await broadcast_typing(chat_id)

    try:
        # Process message through agent
        agent = AgentService(db)
        user_message, assistant_message = await agent.process_message(
            chat_id=chat_id,
            user_content=body.content,
        )

        # Broadcast new messages via SSE
        await broadcast_message(chat_id, _convert_message(user_message))
        await broadcast_message(chat_id, _convert_message(assistant_message))

        return SendMessageResponse(
            user_message=_convert_message(user_message),
            assistant_message=_convert_message(assistant_message),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(f"Error processing message: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to process message with LLM",
        )
