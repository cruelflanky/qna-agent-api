# QnA Agent API - Project Documentation

## Overview

Production-ready QnA agent API that answers questions using OpenAI-compatible LLM and a local knowledge base.

## Tech Stack

| Component | Technology |
|-----------|------------|
| Framework | FastAPI |
| Database | SQLite (async via aiosqlite) |
| ORM | SQLAlchemy 2.0 (async) |
| LLM Client | OpenAI Python SDK |
| Package Manager | uv |
| Testing | pytest + pytest-asyncio |
| Real-time | Server-Sent Events (SSE) |
| Containerization | Docker (multi-stage) |
| Orchestration | Kubernetes |

## Project Structure

```
qna-agent/
├── src/qna_agent/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app, lifespan, health endpoints
│   ├── config.py               # Pydantic Settings (env-based config)
│   ├── database.py             # Async SQLite connection
│   ├── models/
│   │   ├── db.py               # SQLAlchemy ORM models
│   │   └── schemas.py          # Pydantic request/response schemas
│   ├── routers/
│   │   ├── chats.py            # Chat sessions CRUD
│   │   ├── messages.py         # Messages + AI responses
│   │   └── events.py           # SSE endpoint
│   ├── services/
│   │   ├── agent.py            # OpenAI agent with tool calling
│   │   ├── knowledge.py        # Knowledge base operations
│   │   └── chat.py             # Chat/message business logic
│   └── tools/
│       └── definitions.py      # OpenAI function definitions
├── knowledge/                   # Knowledge base text files
├── tests/
│   ├── conftest.py             # Test fixtures
│   ├── test_chats.py
│   ├── test_messages.py
│   └── test_agent.py
├── kubernetes/
│   ├── deployment.yaml
│   ├── service.yaml
│   └── configmap.yaml
├── docs/                        # This documentation
├── Dockerfile
├── pyproject.toml
├── .env.example
└── README.md
```

## Quick Start

### Prerequisites

- Python 3.12+
- uv package manager
- OpenRouter API key (or local Ollama)

### Local Development

```bash
# Clone and setup
cd qna-agent
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your OPENAI_API_KEY

# Initialize database
uv run python -m qna_agent.database

# Run server
uv run uvicorn qna_agent.main:app --reload

# Run tests
uv run pytest
```

### Docker

```bash
# Build
docker build -t qna-agent:latest .

# Run
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=your-key \
  -e OPENAI_BASE_URL=https://openrouter.ai/api/v1 \
  -v ./knowledge:/app/knowledge \
  -v ./data:/app/data \
  qna-agent:latest
```

### Kubernetes

```bash
# Create secret for API key
kubectl create secret generic qna-agent-secrets \
  --from-literal=openai-api-key=your-key

# Deploy
kubectl apply -f kubernetes/
```

## Documentation Index

- [ARCHITECTURE.md](./ARCHITECTURE.md) - Design decisions and architecture
- [API.md](./API.md) - API specification and examples
- [PRODUCTION.md](./PRODUCTION.md) - Production deployment considerations

## Configuration

All configuration is done via environment variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | - | API key for LLM provider |
| `OPENAI_BASE_URL` | No | `https://api.openai.com/v1` | LLM API base URL |
| `OPENAI_MODEL` | No | `gpt-3.5-turbo` | Model to use |
| `DATABASE_URL` | No | `sqlite+aiosqlite:///./data/qna.db` | Database connection |
| `KNOWLEDGE_DIR` | No | `./knowledge` | Path to knowledge base |
| `HOST` | No | `0.0.0.0` | Server bind host |
| `PORT` | No | `8000` | Server bind port |
| `LOG_LEVEL` | No | `INFO` | Logging level |

## Implementation Phases

For detailed step-by-step implementation guide, see:

1. [Phase 1: Project Setup](phases/01-project-setup.md)
2. [Phase 2: Database Layer](phases/02-database.md)
3. [Phase 3: Chat Management](phases/03-chat-management.md)
4. [Phase 4: Knowledge Base](phases/04-knowledge-base.md)
5. [Phase 5: Agent Implementation](phases/05-agent.md)
6. [Phase 6: Messages & SSE](phases/06-messages-sse.md)
7. [Phase 7: Health & Production](phases/07-health-production.md)
8. [Phase 8: Testing](phases/08-testing.md)
9. [Phase 9: Docker](phases/09-docker.md)
10. [Phase 10: Kubernetes](phases/10-kubernetes.md)
11. [Phase 11: Documentation](phases/11-documentation.md)

## License

MIT
