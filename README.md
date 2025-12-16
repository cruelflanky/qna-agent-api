# QnA Agent API

Production-ready QnA agent API using OpenAI-compatible LLMs with function calling and local knowledge base.

## Tech Stack

- **FastAPI** + async SQLite (aiosqlite)
- **OpenAI SDK** with function calling (no LangChain)
- **SSE** for real-time notifications
- **Docker** multi-stage build, non-root
- **Kubernetes** ready

## Quick Start (Local)

```bash
cp .env.example .env
# Set OPENAI_API_KEY in .env

docker compose up
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

## Kubernetes Deployment

### 1. Build and push image

```bash
docker build -t your-registry/qna-agent:latest .
docker push your-registry/qna-agent:latest
```

### 2. Update image in deployment

```bash
# Edit kubernetes/deployment.yaml
# Change: image: qna-agent:latest
# To: image: your-registry/qna-agent:latest
```

### 3. Create secret

```bash
kubectl create secret generic qna-agent-secrets \
  --from-literal=OPENAI_API_KEY=sk-your-key
```

### 4. Deploy

```bash
kubectl apply -f kubernetes/
```

### 5. Verify

```bash
kubectl get pods -l app=qna-agent
kubectl logs -l app=qna-agent -f
```

### 6. Access

```bash
# Port forward for testing
kubectl port-forward svc/qna-agent 8000:80

# Or configure Ingress for production domain
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/chats` | Create chat session |
| GET | `/chats` | List chats |
| DELETE | `/chats/{id}` | Delete chat |
| POST | `/chats/{id}/messages` | Send message, get AI response |
| GET | `/chats/{id}/messages` | Get message history |
| GET | `/chats/{id}/events` | SSE notifications |
| GET | `/health` | Liveness probe |
| GET | `/ready` | Readiness probe |

## Configuration

| Variable | Required | Default |
|----------|----------|---------|
| `OPENAI_API_KEY` | Yes | - |
| `OPENAI_BASE_URL` | No | OpenRouter |
| `OPENAI_MODEL` | No | mistralai/devstral-2512:free |
| `DATABASE_URL` | No | sqlite:///./data/qna.db |
| `LOG_LEVEL` | No | INFO |

## License

MIT
