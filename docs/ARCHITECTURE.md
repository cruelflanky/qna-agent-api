# Architecture & Design Decisions

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client                                   │
└─────────────────────┬───────────────────────────────────────────┘
                      │ HTTP/SSE
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Application                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Routers   │  │  Services   │  │        Agent            │  │
│  │             │  │             │  │  ┌─────────────────┐    │  │
│  │ - chats     │──│ - chat      │──│  │  OpenAI Client  │    │  │
│  │ - messages  │  │ - knowledge │  │  │  (function call)│    │  │
│  │ - events    │  │             │  │  └────────┬────────┘    │  │
│  └─────────────┘  └─────────────┘  │           │             │  │
│         │                          │           ▼             │  │
│         │                          │  ┌─────────────────┐    │  │
│         │                          │  │  KB Search Tool │    │  │
│         │                          │  └─────────────────┘    │  │
│         │                          └─────────────────────────┘  │
│         ▼                                                        │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    SQLite Database                          ││
│  │  (chats, messages tables via SQLAlchemy async)              ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                                        │
                      ┌─────────────────┴─────────────────┐
                      ▼                                   ▼
            ┌─────────────────┐                 ┌─────────────────┐
            │  Knowledge Base │                 │  OpenRouter/    │
            │  (./knowledge/) │                 │  Ollama LLM     │
            └─────────────────┘                 └─────────────────┘
```

## Design Decisions

### 1. Async SQLite (aiosqlite + SQLAlchemy)

**Decision:** Use async SQLite instead of sync operations.

**Rationale:**
- FastAPI is async-first, blocking DB calls would hurt performance
- aiosqlite provides true async I/O for SQLite
- SQLAlchemy 2.0 has first-class async support
- SQLite is explicitly required by the task

**Trade-offs:**
- SQLite has write lock limitations (single writer)
- For high concurrency, PostgreSQL would be better (documented in PRODUCTION.md)

### 2. Server-Sent Events for Real-time Updates

**Decision:** Use SSE instead of WebSockets for client notifications.

**Rationale:**
- Notifications are server-to-client only (one-way)
- SSE is simpler to implement and debug
- Built-in reconnection in browsers
- Works naturally with HTTP/2
- Better suited for Kubernetes (no sticky sessions required)
- Uses `sse-starlette` library for clean FastAPI integration

**Event Types:**
```
event: message
data: {"id": "msg_xxx", "role": "assistant", "content": "..."}

event: typing
data: {"chat_id": "chat_xxx"}

event: error
data: {"message": "..."}
```

### 3. OpenAI Function Calling for Knowledge Base

**Decision:** Agent uses OpenAI function calling to query knowledge base.

**Rationale:**
- Task explicitly requires tool/function calling
- Agent decides when to search (not every message)
- Clean separation between agent logic and KB implementation
- Allows agent to make multiple searches if needed

**Tool Definition:**
```python
{
    "type": "function",
    "function": {
        "name": "search_knowledge_base",
        "description": "Search the knowledge base for relevant information",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query to find relevant documents"
                }
            },
            "required": ["query"]
        }
    }
}
```

**Agent Loop:**
1. Receive user message
2. Send to LLM with conversation history + tool definition
3. If LLM returns tool_call → execute KB search → send result back to LLM
4. Repeat until LLM returns final text response
5. Persist all messages (user, assistant, tool calls, tool results)

### 4. Simple Text-Based Knowledge Base

**Decision:** Plain text files with filename + content search.

**Rationale:**
- Task specifies "plain text files in a designated directory"
- Simple is better for assessment scope
- Easy to extend to vector search later

**Search Strategy:**
1. List all `.txt` files in `KNOWLEDGE_DIR`
2. Score by: filename match (weighted higher) + content substring match
3. Return top-N results with content

**Future Enhancement (TODO):**
- Vector embeddings with FAISS/ChromaDB
- Semantic search instead of keyword matching

### 5. Pydantic Settings for Configuration

**Decision:** Use `pydantic-settings` for all configuration.

**Rationale:**
- Type-safe configuration with validation
- Automatic environment variable loading
- Support for `.env` files in development
- Clear documentation of required/optional settings
- Production standard for FastAPI applications

```python
class Settings(BaseSettings):
    openai_api_key: str
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-3.5-turbo"
    database_url: str = "sqlite+aiosqlite:///./data/qna.db"
    knowledge_dir: Path = Path("./knowledge")

    model_config = SettingsConfigDict(env_file=".env")
```

### 6. Layered Architecture

**Decision:** Separate routers, services, and data access.

```
Routers (HTTP handling)
    ↓
Services (business logic)
    ↓
Database (data access via SQLAlchemy)
```

**Rationale:**
- Clear separation of concerns
- Easier testing (mock services, not HTTP)
- Services can be reused (e.g., in background tasks)
- Standard enterprise pattern

### 7. UUID-Based Identifiers

**Decision:** Use UUIDs for all entity IDs.

**Rationale:**
- No sequential ID leakage
- Safe for distributed systems
- No DB roundtrip needed to generate ID
- Standard practice for APIs

### 8. Conversation Context Management

**Decision:** Store full message history, send to LLM on each request.

**Rationale:**
- Simple and stateless (API server doesn't hold state)
- LLM sees full context each time
- Easy to implement pagination/limits later

**Message Storage:**
```sql
messages (
    id TEXT PRIMARY KEY,
    chat_id TEXT REFERENCES chats(id),
    role TEXT,        -- 'user', 'assistant', 'system', 'tool'
    content TEXT,
    tool_calls TEXT,  -- JSON for function calls made by assistant
    tool_call_id TEXT -- For tool response messages
)
```

### 9. Health Check Design

**Decision:** Separate liveness (`/health`) and readiness (`/ready`) endpoints.

**Liveness (`/health`):**
- Always returns 200 if app is running
- Used by K8s to detect crashed containers

**Readiness (`/ready`):**
- Checks database connectivity
- Optionally checks LLM API connectivity
- Used by K8s to know when to route traffic

### 10. Error Handling Strategy

**Decision:** Use FastAPI's HTTPException with appropriate status codes.

| Scenario | Status Code |
|----------|-------------|
| Chat not found | 404 Not Found |
| Invalid input | 422 Unprocessable Entity |
| LLM API error | 502 Bad Gateway |
| Internal error | 500 Internal Server Error |

All errors return JSON:
```json
{
    "detail": "Chat not found"
}
```

## Database Schema

```sql
CREATE TABLE chats (
    id TEXT PRIMARY KEY,
    title TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    chat_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system', 'tool')),
    content TEXT,
    tool_calls TEXT,
    tool_call_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_messages_chat_id ON messages(chat_id);
```

## Dependencies

| Package | Purpose |
|---------|---------|
| fastapi | Web framework |
| uvicorn | ASGI server |
| openai | LLM client |
| sqlalchemy[asyncio] | ORM with async support |
| aiosqlite | Async SQLite driver |
| pydantic-settings | Configuration management |
| sse-starlette | Server-Sent Events |
| httpx | Async HTTP client (for testing) |
| pytest | Testing framework |
| pytest-asyncio | Async test support |

## Not Using (Per Requirements)

- LangChain, LlamaIndex, or other agentic frameworks
- Vector databases (keeping it simple with text search)
- Redis/external caching
- Background task queues (Celery, etc.)
