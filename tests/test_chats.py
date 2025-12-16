import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_chat(client: AsyncClient):
    """Test creating a new chat session."""
    response = await client.post(
        "/chats",
        json={"title": "Test Chat"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Chat"
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_chat_without_title(client: AsyncClient):
    """Test creating a chat without title."""
    response = await client.post("/chats", json={})
    assert response.status_code == 201
    data = response.json()
    assert data["title"] is None


@pytest.mark.asyncio
async def test_list_chats(client: AsyncClient):
    """Test listing chat sessions."""
    # Create a few chats
    await client.post("/chats", json={"title": "Chat 1"})
    await client.post("/chats", json={"title": "Chat 2"})

    response = await client.get("/chats")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert len(data["items"]) >= 2


@pytest.mark.asyncio
async def test_list_chats_pagination(client: AsyncClient):
    """Test chat list pagination."""
    # Create 5 chats
    for i in range(5):
        await client.post("/chats", json={"title": f"Chat {i}"})

    # Get first page
    response = await client.get("/chats?limit=2&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["limit"] == 2
    assert data["offset"] == 0


@pytest.mark.asyncio
async def test_get_chat(client: AsyncClient):
    """Test getting a specific chat."""
    # Create chat
    create_response = await client.post(
        "/chats",
        json={"title": "Test Chat"},
    )
    chat_id = create_response.json()["id"]

    # Get chat
    response = await client.get(f"/chats/{chat_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == chat_id
    assert data["title"] == "Test Chat"


@pytest.mark.asyncio
async def test_get_chat_not_found(client: AsyncClient):
    """Test getting non-existent chat."""
    response = await client.get("/chats/non-existent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_chat(client: AsyncClient):
    """Test deleting a chat."""
    # Create chat
    create_response = await client.post(
        "/chats",
        json={"title": "To Delete"},
    )
    chat_id = create_response.json()["id"]

    # Delete chat
    response = await client.delete(f"/chats/{chat_id}")
    assert response.status_code == 204

    # Verify deleted
    get_response = await client.get(f"/chats/{chat_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_chat_not_found(client: AsyncClient):
    """Test deleting non-existent chat."""
    response = await client.delete("/chats/non-existent-id")
    assert response.status_code == 404
