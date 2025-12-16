import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_messages_empty(client: AsyncClient):
    """Test getting messages for a new chat."""
    # Create chat
    create_response = await client.post("/chats", json={})
    chat_id = create_response.json()["id"]

    # Get messages
    response = await client.get(f"/chats/{chat_id}/messages")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_get_messages_chat_not_found(client: AsyncClient):
    """Test getting messages for non-existent chat."""
    response = await client.get("/chats/non-existent/messages")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_send_message_chat_not_found(client: AsyncClient):
    """Test sending message to non-existent chat."""
    response = await client.post(
        "/chats/non-existent/messages",
        json={"content": "Hello"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_send_message_empty_content(client: AsyncClient):
    """Test sending message with empty content."""
    # Create chat
    create_response = await client.post("/chats", json={})
    chat_id = create_response.json()["id"]

    # Try to send empty message
    response = await client.post(
        f"/chats/{chat_id}/messages",
        json={"content": ""},
    )
    assert response.status_code == 422  # Validation error
