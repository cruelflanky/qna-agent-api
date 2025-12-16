# API Specification

Base URL: `http://localhost:8000`

## Endpoints Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/chats` | Create new chat session |
| GET | `/chats` | List all chats |
| GET | `/chats/{id}` | Get chat details |
| DELETE | `/chats/{id}` | Delete chat |
| GET | `/chats/{id}/messages` | Get message history |
| POST | `/chats/{id}/messages` | Send message |
| GET | `/chats/{id}/events` | SSE stream |
| GET | `/health` | Liveness probe |
| GET | `/ready` | Readiness probe |

---

## Chat Sessions

### Create Chat

```http
POST /chats
Content-Type: application/json
```

**Request Body (optional):**
```json
{
    "title": "My Chat Session"
}
```

**Response:** `201 Created`
```json
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "My Chat Session",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/chats \
  -H "Content-Type: application/json" \
  -d '{"title": "Knowledge Base Q&A"}'
```

---

### List Chats

```http
GET /chats?limit=20&offset=0
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| limit | int | 20 | Max results (1-100) |
| offset | int | 0 | Pagination offset |

**Response:** `200 OK`
```json
{
    "items": [
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "title": "Knowledge Base Q&A",
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T10:35:00Z"
        }
    ],
    "total": 1,
    "limit": 20,
    "offset": 0
}
```

**Example:**
```bash
curl http://localhost:8000/chats
```

---

### Get Chat

```http
GET /chats/{id}
```

**Response:** `200 OK`
```json
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "Knowledge Base Q&A",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:35:00Z"
}
```

**Error:** `404 Not Found`
```json
{
    "detail": "Chat not found"
}
```

**Example:**
```bash
curl http://localhost:8000/chats/550e8400-e29b-41d4-a716-446655440000
```

---

### Delete Chat

```http
DELETE /chats/{id}
```

**Response:** `204 No Content`

**Error:** `404 Not Found`

**Example:**
```bash
curl -X DELETE http://localhost:8000/chats/550e8400-e29b-41d4-a716-446655440000
```

---

## Messages

### Get Message History

```http
GET /chats/{id}/messages?limit=50&offset=0
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| limit | int | 50 | Max messages (1-100) |
| offset | int | 0 | Pagination offset |

**Response:** `200 OK`
```json
{
    "items": [
        {
            "id": "msg-001",
            "chat_id": "550e8400-e29b-41d4-a716-446655440000",
            "role": "user",
            "content": "What is our refund policy?",
            "tool_calls": null,
            "tool_call_id": null,
            "created_at": "2024-01-15T10:31:00Z"
        },
        {
            "id": "msg-002",
            "chat_id": "550e8400-e29b-41d4-a716-446655440000",
            "role": "assistant",
            "content": null,
            "tool_calls": [
                {
                    "id": "call_abc123",
                    "type": "function",
                    "function": {
                        "name": "search_knowledge_base",
                        "arguments": "{\"query\": \"refund policy\"}"
                    }
                }
            ],
            "tool_call_id": null,
            "created_at": "2024-01-15T10:31:01Z"
        },
        {
            "id": "msg-003",
            "chat_id": "550e8400-e29b-41d4-a716-446655440000",
            "role": "tool",
            "content": "Found in refund-policy.txt: Our refund policy allows returns within 30 days...",
            "tool_calls": null,
            "tool_call_id": "call_abc123",
            "created_at": "2024-01-15T10:31:02Z"
        },
        {
            "id": "msg-004",
            "chat_id": "550e8400-e29b-41d4-a716-446655440000",
            "role": "assistant",
            "content": "Based on our knowledge base, our refund policy allows returns within 30 days of purchase...",
            "tool_calls": null,
            "tool_call_id": null,
            "created_at": "2024-01-15T10:31:03Z"
        }
    ],
    "total": 4,
    "limit": 50,
    "offset": 0
}
```

**Example:**
```bash
curl http://localhost:8000/chats/550e8400-e29b-41d4-a716-446655440000/messages
```

---

### Send Message

```http
POST /chats/{id}/messages
Content-Type: application/json
```

**Request Body:**
```json
{
    "content": "What is our refund policy?"
}
```

**Response:** `201 Created`
```json
{
    "user_message": {
        "id": "msg-001",
        "chat_id": "550e8400-e29b-41d4-a716-446655440000",
        "role": "user",
        "content": "What is our refund policy?",
        "created_at": "2024-01-15T10:31:00Z"
    },
    "assistant_message": {
        "id": "msg-004",
        "chat_id": "550e8400-e29b-41d4-a716-446655440000",
        "role": "assistant",
        "content": "Based on our knowledge base, our refund policy allows returns within 30 days of purchase...",
        "created_at": "2024-01-15T10:31:03Z"
    }
}
```

**Errors:**
- `404 Not Found` - Chat doesn't exist
- `422 Unprocessable Entity` - Invalid input
- `502 Bad Gateway` - LLM API error

**Example:**
```bash
curl -X POST http://localhost:8000/chats/550e8400-e29b-41d4-a716-446655440000/messages \
  -H "Content-Type: application/json" \
  -d '{"content": "What is our refund policy?"}'
```

---

## Real-time Events (SSE)

### Subscribe to Chat Events

```http
GET /chats/{id}/events
Accept: text/event-stream
```

**Response:** Server-Sent Events stream

**Event Types:**

1. **message** - New message in chat
```
event: message
data: {"id": "msg-004", "role": "assistant", "content": "Based on our knowledge base..."}
```

2. **typing** - Agent is processing
```
event: typing
data: {"chat_id": "550e8400-e29b-41d4-a716-446655440000"}
```

3. **error** - Error occurred
```
event: error
data: {"message": "Failed to process message"}
```

**Example (curl):**
```bash
curl -N http://localhost:8000/chats/550e8400-e29b-41d4-a716-446655440000/events
```

**Example (JavaScript):**
```javascript
const eventSource = new EventSource(
    'http://localhost:8000/chats/550e8400-e29b-41d4-a716-446655440000/events'
);

eventSource.addEventListener('message', (event) => {
    const data = JSON.parse(event.data);
    console.log('New message:', data);
});

eventSource.addEventListener('typing', (event) => {
    console.log('Agent is typing...');
});

eventSource.addEventListener('error', (event) => {
    const data = JSON.parse(event.data);
    console.error('Error:', data.message);
});
```

---

## Health Endpoints

### Liveness Probe

```http
GET /health
```

**Response:** `200 OK`
```json
{
    "status": "healthy"
}
```

Used by Kubernetes liveness probe. Returns 200 if the application is running.

---

### Readiness Probe

```http
GET /ready
```

**Response:** `200 OK`
```json
{
    "status": "ready",
    "checks": {
        "database": "ok",
        "llm_api": "ok"
    }
}
```

**Response (not ready):** `503 Service Unavailable`
```json
{
    "status": "not_ready",
    "checks": {
        "database": "ok",
        "llm_api": "error: connection timeout"
    }
}
```

Used by Kubernetes readiness probe. Returns 200 only when all dependencies are available.

---

## Error Responses

All errors return JSON with a `detail` field:

```json
{
    "detail": "Error message here"
}
```

**Status Codes:**
| Code | Description |
|------|-------------|
| 400 | Bad Request - Invalid input |
| 404 | Not Found - Resource doesn't exist |
| 422 | Unprocessable Entity - Validation error |
| 500 | Internal Server Error |
| 502 | Bad Gateway - LLM API error |
| 503 | Service Unavailable - Not ready |

---

## OpenAPI Documentation

When the server is running, interactive documentation is available at:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI JSON:** http://localhost:8000/openapi.json
