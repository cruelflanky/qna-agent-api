from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from qna_agent.config import get_settings


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""
    pass


# Global engine and session factory (initialized in lifespan)
engine = None
async_session_factory = None


async def init_db() -> None:
    """Initialize database engine and create tables."""
    global engine, async_session_factory

    settings = get_settings()

    # Create async engine
    engine = create_async_engine(
        settings.database_url,
        echo=settings.log_level == "DEBUG",
    )

    # Create session factory
    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    global engine
    if engine:
        await engine.dispose()


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session."""
    if async_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database session."""
    async with get_session() as session:
        yield session
