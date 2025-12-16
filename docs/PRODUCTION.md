# Production Deployment Considerations

This document addresses the production considerations mentioned in the assessment requirements.

---

## 1. Sensitive Configuration in Kubernetes

### Current Implementation

The application uses environment variables for all configuration, supporting:
- Direct environment variables
- `.env` files (development only)

### Recommended Approach for K8s

**Option A: Kubernetes Secrets (Basic)**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: qna-agent-secrets
type: Opaque
stringData:
  openai-api-key: "sk-or-v1-xxx"
---
# In Deployment
env:
  - name: OPENAI_API_KEY
    valueFrom:
      secretKeyRef:
        name: qna-agent-secrets
        key: openai-api-key
```

**Option B: External Secrets Operator (Recommended for Production)**
```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: qna-agent-secrets
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-backend
    kind: ClusterSecretStore
  target:
    name: qna-agent-secrets
  data:
    - secretKey: openai-api-key
      remoteRef:
        key: secret/qna-agent
        property: api_key
```

**Option C: HashiCorp Vault with Sidecar**
- Use Vault Agent Injector for automatic secret injection
- Secrets are mounted as files in `/vault/secrets/`
- Auto-rotation support

### Security Best Practices

- Never commit secrets to git (use `.gitignore`)
- Rotate API keys regularly
- Use RBAC to limit secret access
- Enable encryption at rest for etcd
- Audit secret access

---

## 2. Service Lifecycle Management (Health Endpoints)

### Implemented Endpoints

| Endpoint | Purpose | K8s Probe |
|----------|---------|-----------|
| `/health` | Application is running | Liveness |
| `/ready` | Dependencies are available | Readiness |

### Liveness Probe (`/health`)

- Returns `200` if the FastAPI app is responding
- Used to detect deadlocks or hung processes
- Failure triggers pod restart

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 15
  timeoutSeconds: 5
  failureThreshold: 3
```

### Readiness Probe (`/ready`)

- Checks database connectivity
- Optionally validates LLM API access
- Failure removes pod from service endpoints

```yaml
readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3
```

### Startup Probe (Optional)

For slow-starting applications:
```yaml
startupProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
  failureThreshold: 30
```

### Graceful Shutdown

The application handles `SIGTERM` gracefully via FastAPI's lifespan:
- Stops accepting new requests
- Completes in-flight requests
- Closes database connections
- Exits cleanly

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()
```

K8s configuration:
```yaml
terminationGracePeriodSeconds: 30
```

---

## 3. Observability

### Current Implementation

- Structured JSON logging (production)
- Request ID in all log entries
- Error tracking with stack traces

### Logging

```python
# Structured log output
{
    "timestamp": "2024-01-15T10:30:00Z",
    "level": "INFO",
    "request_id": "abc-123",
    "message": "Processing message",
    "chat_id": "550e8400-...",
    "duration_ms": 150
}
```

### TODO: Metrics (Prometheus)

Add `/metrics` endpoint with:
```python
# Request metrics
http_requests_total{method="POST", endpoint="/chats/{id}/messages", status="200"}
http_request_duration_seconds{method="POST", endpoint="/chats/{id}/messages"}

# Business metrics
chat_sessions_total
messages_total{role="user|assistant"}
llm_calls_total{status="success|error"}
llm_call_duration_seconds
knowledge_base_searches_total
```

Implementation with `prometheus-fastapi-instrumentator`:
```python
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app)
```

### TODO: Distributed Tracing

For microservice environments:
- OpenTelemetry integration
- Trace context propagation
- Spans for LLM calls, DB operations

```python
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

FastAPIInstrumentor.instrument_app(app)
```

### Recommended Stack

- **Metrics:** Prometheus + Grafana
- **Logs:** Loki or ELK Stack
- **Traces:** Jaeger or Tempo
- **Unified:** Grafana Cloud or Datadog

---

## 4. Persistent Data in Containers

### Challenge

SQLite stores data in a file. Container restarts lose data.

### Solution A: PersistentVolumeClaim (Current SQLite)

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: qna-agent-data
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
---
# In Deployment
volumeMounts:
  - name: data
    mountPath: /app/data
volumes:
  - name: data
    persistentVolumeClaim:
      claimName: qna-agent-data
```

**Limitations:**
- `ReadWriteOnce` = single pod only (no horizontal scaling)
- SQLite has write locking issues with concurrent access

### Solution B: External Database (Recommended)

For production with multiple replicas:

```yaml
# Environment variable change
DATABASE_URL=postgresql+asyncpg://user:pass@postgres-service:5432/qna

# Or use cloud-managed:
# - AWS RDS
# - Google Cloud SQL
# - Azure Database for PostgreSQL
```

Benefits:
- Horizontal scaling
- Automatic backups
- Point-in-time recovery
- High availability

### Knowledge Base Persistence

Mount knowledge base as ConfigMap or PVC:

```yaml
# ConfigMap for small, static KB
apiVersion: v1
kind: ConfigMap
metadata:
  name: knowledge-base
data:
  refund-policy.txt: |
    Our refund policy allows returns within 30 days...
---
# Or PVC for larger/dynamic KB
volumeMounts:
  - name: knowledge
    mountPath: /app/knowledge
```

---

## 5. TLS Termination

### Recommended: Ingress-level TLS

Do NOT handle TLS in the application. Terminate at ingress/load balancer.

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: qna-agent-ingress
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
    - hosts:
        - qna-api.example.com
      secretName: qna-agent-tls
  rules:
    - host: qna-api.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: qna-agent
                port:
                  number: 8000
```

### Benefits of Ingress TLS

- Certificate management via cert-manager
- Automatic renewal (Let's Encrypt)
- Centralized SSL configuration
- TLS offloading reduces app CPU usage

### Port Configuration

Application always runs on HTTP (port 8000). External access:
- Development: `http://localhost:8000`
- Production: `https://qna-api.example.com` (443 → Ingress → 8000)

---

## 6. Performance Improvements (Bonus)

### Immediate Wins

1. **Connection Pooling**
   - SQLAlchemy pool size tuning
   - OpenAI client connection reuse

2. **Response Caching**
   - Cache knowledge base search results
   - Short TTL for frequently asked questions

3. **Async All The Way**
   - Already using async SQLite
   - Ensure no blocking calls in request path

### Medium-term Improvements

1. **Vector Search for Knowledge Base**
   - Replace text search with embeddings
   - Use FAISS, ChromaDB, or pgvector
   - Better relevance, faster queries

2. **Streaming Responses**
   - Stream LLM output token-by-token via SSE
   - Better perceived latency

3. **Read Replicas**
   - PostgreSQL read replicas for message history
   - Reduce load on primary

### Long-term Architecture

1. **Message Queue for Async Processing**
   - Redis/RabbitMQ for message processing
   - Non-blocking message handling

2. **Horizontal Scaling**
   - Stateless application design (already done)
   - PostgreSQL instead of SQLite
   - Shared nothing architecture

3. **CDN for Static Content**
   - If serving any static files
   - Reduce latency for global users

---

## Kubernetes Deployment Checklist

- [ ] Secrets created (not in git)
- [ ] PersistentVolumeClaim for data
- [ ] Resource limits set (CPU/memory)
- [ ] Liveness/readiness probes configured
- [ ] Horizontal Pod Autoscaler (optional)
- [ ] Network policies (optional)
- [ ] Ingress with TLS
- [ ] Pod Disruption Budget (for HA)
- [ ] Service account with minimal RBAC

---

## Example Production Values

```yaml
# deployment.yaml resources section
resources:
  requests:
    memory: "256Mi"
    cpu: "100m"
  limits:
    memory: "512Mi"
    cpu: "500m"

# HPA (optional)
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: qna-agent-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: qna-agent
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```
