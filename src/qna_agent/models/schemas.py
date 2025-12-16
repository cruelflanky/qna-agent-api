from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ============ Chat Schemas ============

class ChatCreate(BaseModel):
    """Schema for creating a chat."""
    title: str | None = Field(None, max_length=255)


class ChatResponse(BaseModel):
    """Schema for chat response."""
    id: str
    title: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatListResponse(BaseModel):
    """Schema for paginated chat list."""
    items: list[ChatResponse]
    total: int
    limit: int
    offset: int


# ============ Message Schemas ============

class MessageCreate(BaseModel):
    """Schema for creating a message."""
    content: str = Field(..., min_length=1, max_length=10000)


class ToolCall(BaseModel):
    """Schema for tool call in message."""
    id: str
    type: str = "function"
    function: dict[str, Any]


class MessageResponse(BaseModel):
    """Schema for message response."""
    id: str
    chat_id: str
    role: str
    content: str | None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageListResponse(BaseModel):
    """Schema for paginated message list."""
    items: list[MessageResponse]
    total: int
    limit: int
    offset: int


class SendMessageResponse(BaseModel):
    """Schema for send message response."""
    user_message: MessageResponse
    assistant_message: MessageResponse


# ============ Health Schemas ============

class HealthResponse(BaseModel):
    """Schema for health check response."""
    status: str


class ReadyResponse(BaseModel):
    """Schema for readiness check response."""
    status: str
    checks: dict[str, str]


# ============ SSE Event Schemas ============

class SSEMessageEvent(BaseModel):
    """SSE message event data."""
    id: str
    role: str
    content: str | None


class SSETypingEvent(BaseModel):
    """SSE typing event data."""
    chat_id: str


class SSEErrorEvent(BaseModel):
    """SSE error event data."""
    message: str
