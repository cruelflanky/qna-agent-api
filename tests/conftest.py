import asyncio
import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from qna_agent.database import Base, get_db
from qna_agent.main import app

# Set default test configuration
# For integration tests, set OPENAI_API_KEY environment variable
os.environ.setdefault("OPENAI_API_KEY", "test-key-for-unit-tests")
os.environ.setdefault("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
os.environ.setdefault("OPENAI_MODEL", "mistralai/devstral-2512:free")

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with async_session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(test_engine) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client with test database."""
    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def override_get_db():
        async with async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def knowledge_dir(tmp_path):
    """Create temporary knowledge base directory with test files."""
    kb_dir = tmp_path / "knowledge"
    kb_dir.mkdir()

    # Create test KB files
    (kb_dir / "test-policy.txt").write_text(
        "Test Policy\n\nThis is a test policy document.\n"
        "Our return policy allows returns within 30 days.\n"
        "All items must be in original condition."
    )
    (kb_dir / "faq.txt").write_text(
        "Frequently Asked Questions\n\n"
        "Q: What are your business hours?\n"
        "A: We are open Monday to Friday, 9 AM to 5 PM.\n\n"
        "Q: How can I contact support?\n"
        "A: Email us at support@example.com"
    )

    # Set environment variable for tests
    os.environ["KNOWLEDGE_DIR"] = str(kb_dir)

    yield kb_dir

    # Cleanup
    if "KNOWLEDGE_DIR" in os.environ:
        del os.environ["KNOWLEDGE_DIR"]
