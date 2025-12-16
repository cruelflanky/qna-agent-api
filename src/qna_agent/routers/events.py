import asyncio
import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from qna_agent.database import get_db
from qna_agent.models.schemas import MessageResponse, SSEMessageEvent, SSETypingEvent
from qna_agent.services.chat import ChatService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["events"])

# Simple in-memory event queues per chat
# In production, use Redis pub/sub for multi-instance support
_chat_queues: dict[str, list[asyncio.Queue]] = {}


def _get_chat_queues(chat_id: str) -> list[asyncio.Queue]:
    """Get or create queue list for a chat."""
    if chat_id not in _chat_queues:
        _chat_queues[chat_id] = []
    return _chat_queues[chat_id]


async def broadcast_message(chat_id: str, message: MessageResponse) -> None:
    """Broadcast a message event to all SSE clients for a chat."""
    queues = _get_chat_queues(chat_id)
    event = {
        "event": "message",
        "data": SSEMessageEvent(
            id=message.id,
            role=message.role,
            content=message.content,
        ).model_dump_json(),
    }
    for queue in queues:
        await queue.put(event)


async def broadcast_typing(chat_id: str) -> None:
    """Broadcast a typing indicator to all SSE clients for a chat."""
    queues = _get_chat_queues(chat_id)
    event = {
        "event": "typing",
        "data": SSETypingEvent(chat_id=chat_id).model_dump_json(),
    }
    for queue in queues:
        await queue.put(event)


async def broadcast_error(chat_id: str, message: str) -> None:
    """Broadcast an error event to all SSE clients for a chat."""
    queues = _get_chat_queues(chat_id)
    event = {
        "event": "error",
        "data": json.dumps({"message": message}),
    }
    for queue in queues:
        await queue.put(event)


async def _event_generator(
    chat_id: str,
    queue: asyncio.Queue,
) -> AsyncGenerator[dict, None]:
    """Generate SSE events for a chat."""
    try:
        while True:
            # Wait for events with timeout (for keepalive)
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield event
            except TimeoutError:
                # Send keepalive comment
                yield {"comment": "keepalive"}
    finally:
        # Remove queue on disconnect
        queues = _get_chat_queues(chat_id)
        if queue in queues:
            queues.remove(queue)
        logger.info(f"SSE client disconnected from chat {chat_id}")


@router.get(
    "/chats/{chat_id}/events",
    summary="Subscribe to chat events via SSE",
)
async def subscribe_to_events(
    chat_id: str,
    db: AsyncSession = Depends(get_db),
) -> EventSourceResponse:
    """
    Subscribe to real-time events for a chat via Server-Sent Events.

    Event types:
    - `message`: New message in the chat
    - `typing`: Agent is processing a message
    - `error`: An error occurred
    """
    # Verify chat exists
    chat_service = ChatService(db)
    chat = await chat_service.get_chat(chat_id)
    if chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )

    # Create queue for this client
    queue: asyncio.Queue = asyncio.Queue()
    queues = _get_chat_queues(chat_id)
    queues.append(queue)

    logger.info(f"SSE client connected to chat {chat_id}")

    return EventSourceResponse(
        _event_generator(chat_id, queue),
        media_type="text/event-stream",
    )
