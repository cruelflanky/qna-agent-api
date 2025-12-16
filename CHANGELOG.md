# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2024-XX-XX

### Added

- Initial release
- Chat session management (CRUD operations)
- Message handling with AI responses
- Knowledge base integration with OpenAI function calling
- Server-Sent Events for real-time notifications
- Health check endpoints (/health, /ready)
- Docker multi-stage build
- Kubernetes deployment manifests
- Comprehensive test suite

### Technical Details

- FastAPI async application
- SQLite database with SQLAlchemy async
- OpenAI SDK with function calling
- SSE via sse-starlette
- uv for dependency management
