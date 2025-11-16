import os
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from typing import Generator

# --- 1. Configuration ---

# The database URL is configured in the environment variables (from docker-compose.yml)
# Fallback for local testing (can be updated to a local Postgres string if preferred)
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./test.db") 

# Create the asynchronous engine
engine = create_async_engine(DATABASE_URL, echo=True)

# Create a session maker for managing database sessions
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# --- 2. Table Creation Function ---

async def create_db_and_tables():
    """Ensures all tables defined in SQLModel metadata are created in the database."""
    print("Attempting to initialize database tables...")
    async with engine.begin() as conn:
        # Runs the synchronous SQLModel.metadata.create_all command within an async context
        await conn.run_sync(SQLModel.metadata.create_all)
    print("Database tables initialized successfully.")

# --- 3. Session Dependency ---

async def get_session() -> Generator[AsyncSession, None, None]:
    """Dependency that provides an asynchronous database session."""
    async with async_session_maker() as session:
        yield session