# QnA Agent API

Production-ready QnA agent API that answers questions using OpenAI-compatible LLMs and a local knowledge base.

## Features

- Chat session management (create, list, delete)
- AI-powered question answering with knowledge base integration
- Real-time notifications via Server-Sent Events (SSE)
- OpenAI function calling for intelligent KB queries
- Production-ready with health endpoints and structured logging

## Tech Stack

- **Framework**: FastAPI
- **Database**: SQLite (async via aiosqlite)
- **LLM**: OpenAI SDK (compatible with OpenRouter, Ollama)
- **Real-time**: Server-Sent Events
- **Package Manager**: uv

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager
- OpenRouter API key (or local Ollama)

### Installation

```bash
# Clone repository
git clone <repository-url>
cd qna-agent

# Install dependencies
uv sync

# Copy environment template
cp .env.example .env

# Edit .env with your API key
# OPENAI_API_KEY=sk-or-v1-your-key
```

### Running Locally

```bash
# Start server
uv run uvicorn qna_agent.main:app --reload

# Server runs at http://localhost:8000
# API docs at http://localhost:8000/docs
```

### Running with Docker

```bash
# Build image
docker build -t qna-agent:latest .

# Run container
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=your-key \
  -v ./knowledge:/app/knowledge:ro \
  qna-agent:latest
```

## API Usage Examples

### Create a Chat Session

```bash
curl -X POST http://localhost:8000/chats \
  -H "Content-Type: application/json" \
  -d '{"title": "My Chat"}'
```

### Send a Message

```bash
curl -X POST http://localhost:8000/chats/{chat_id}/messages \
  -H "Content-Type: application/json" \
  -d '{"content": "What is your refund policy?"}'
```

### Subscribe to Events (SSE)

```bash
curl -N http://localhost:8000/chats/{chat_id}/events
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) - Design decisions
- [API Specification](docs/API.md) - Full API reference
- [Production Guide](docs/PRODUCTION.md) - Deployment considerations
- [Implementation Phases](docs/phases/) - Detailed implementation guide

## Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=qna_agent

# Integration tests (requires API key)
OPENAI_API_KEY=sk-xxx uv run pytest tests/test_agent.py -v
```

## Project Structure

```
qna-agent/
├── src/qna_agent/       # Application source code
├── tests/               # Test suite
├── knowledge/           # Knowledge base files
├── kubernetes/          # K8s manifests
├── docs/                # Documentation
├── Dockerfile           # Container build
└── pyproject.toml       # Project config
```

## License

MIT
