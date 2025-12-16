"""
Integration tests with real LLM calls.
Uses OpenRouter API with real requests - no mocking.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_send_message_and_get_response(client: AsyncClient, knowledge_dir):
    """Test sending a message and getting AI response."""
    # Create chat
    create_response = await client.post("/chats", json={"title": "Test Chat"})
    assert create_response.status_code == 201
    chat_id = create_response.json()["id"]

    # Send message
    response = await client.post(
        f"/chats/{chat_id}/messages",
        json={"content": "Hello! How are you?"},
        timeout=60.0,
    )

    assert response.status_code == 201
    data = response.json()

    # Check response structure
    assert "user_message" in data
    assert "assistant_message" in data
    assert data["user_message"]["role"] == "user"
    assert data["user_message"]["content"] == "Hello! How are you?"
    assert data["assistant_message"]["role"] == "assistant"
    assert data["assistant_message"]["content"] is not None
    assert len(data["assistant_message"]["content"]) > 0


@pytest.mark.asyncio
async def test_send_message_with_kb_query(client: AsyncClient, knowledge_dir):
    """Test sending a message that triggers KB search."""
    # Create chat
    create_response = await client.post("/chats", json={"title": "KB Test"})
    chat_id = create_response.json()["id"]

    # Send message that should trigger KB search
    response = await client.post(
        f"/chats/{chat_id}/messages",
        json={"content": "What is the test policy? What does it say about returns?"},
        timeout=60.0,
    )

    assert response.status_code == 201
    data = response.json()

    # Check we got both messages
    assert "user_message" in data
    assert "assistant_message" in data
    assert data["user_message"]["role"] == "user"
    assert data["assistant_message"]["role"] == "assistant"
    assert data["assistant_message"]["content"] is not None

    # The response should mention something from the KB (returns, 30 days, etc)
    content_lower = data["assistant_message"]["content"].lower()
    # Agent should have found info about returns
    assert any(word in content_lower for word in ["return", "30", "day", "policy", "original"])


@pytest.mark.asyncio
async def test_conversation_context_maintained(client: AsyncClient, knowledge_dir):
    """Test that conversation context is maintained across messages."""
    # Create chat
    create_response = await client.post("/chats", json={})
    chat_id = create_response.json()["id"]

    # Send first message with a fact
    response1 = await client.post(
        f"/chats/{chat_id}/messages",
        json={"content": "Remember this: my favorite color is blue."},
        timeout=60.0,
    )
    assert response1.status_code == 201

    # Send follow-up asking about the fact
    response2 = await client.post(
        f"/chats/{chat_id}/messages",
        json={"content": "What is my favorite color?"},
        timeout=60.0,
    )
    assert response2.status_code == 201
    data = response2.json()

    # The assistant should remember
    content = data["assistant_message"]["content"].lower()
    assert "blue" in content


@pytest.mark.asyncio
async def test_message_history_persisted(client: AsyncClient, knowledge_dir):
    """Test that message history is correctly persisted and retrieved."""
    # Create chat
    create_response = await client.post("/chats", json={})
    chat_id = create_response.json()["id"]

    # Send a message
    await client.post(
        f"/chats/{chat_id}/messages",
        json={"content": "What are your business hours?"},
        timeout=60.0,
    )

    # Get message history
    response = await client.get(f"/chats/{chat_id}/messages")
    assert response.status_code == 200
    data = response.json()

    # Should have at least user message and assistant response
    assert data["total"] >= 2

    # Check roles are present
    roles = [m["role"] for m in data["items"]]
    assert "user" in roles
    assert "assistant" in roles

    # Verify user message content
    user_messages = [m for m in data["items"] if m["role"] == "user"]
    assert len(user_messages) >= 1
    assert user_messages[0]["content"] == "What are your business hours?"


@pytest.mark.asyncio
async def test_multiple_messages_in_conversation(client: AsyncClient, knowledge_dir):
    """Test sending multiple messages in a conversation."""
    # Create chat
    create_response = await client.post("/chats", json={"title": "Multi-turn"})
    chat_id = create_response.json()["id"]

    # First message
    r1 = await client.post(
        f"/chats/{chat_id}/messages",
        json={"content": "Hi there!"},
        timeout=60.0,
    )
    assert r1.status_code == 201

    # Second message
    r2 = await client.post(
        f"/chats/{chat_id}/messages",
        json={"content": "What can you help me with?"},
        timeout=60.0,
    )
    assert r2.status_code == 201

    # Third message - ask about KB
    r3 = await client.post(
        f"/chats/{chat_id}/messages",
        json={"content": "Tell me about the FAQ"},
        timeout=60.0,
    )
    assert r3.status_code == 201

    # Check history
    history = await client.get(f"/chats/{chat_id}/messages")
    data = history.json()

    # Should have at least 6 messages (3 user + 3 assistant, possibly more with tool calls)
    assert data["total"] >= 6
