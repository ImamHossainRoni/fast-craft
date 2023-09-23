from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

# Create an asynchronous SQLAlchemy engine for SQLite
engine = create_async_engine("sqlite+aiosqlite:///db.sqlite3.db", connect_args={"check_same_thread": False})

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
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db = SessionLocal()
    try:
        yield db
    finally:
        await db.close()
