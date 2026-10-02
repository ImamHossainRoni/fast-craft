from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from config import settings

# sqlite's async driver needs check_same_thread=False; other drivers (e.g. asyncpg) don't accept it
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_async_engine(settings.DATABASE_URL, connect_args=connect_args)

# Create an asynchronous session factory using the engine
SessionLocal = async_sessionmaker(engine)
Base = declarative_base()


async def get_db():
    """
    Create an asynchronous database session and manage its lifecycle using FastAPI's dependency injection.

    Returns:
        async_generator: An asynchronous generator that yields the database session.

    Example:
        ```
        async with get_db() as db:
             # Use db for database operations
        ```
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        await db.close()
