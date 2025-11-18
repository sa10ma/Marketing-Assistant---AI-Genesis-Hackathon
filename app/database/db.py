import os
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from typing import Generator, Annotated
from fastapi import Depends


# --- 1. Configuration ---
POSTGRES_USER = os.environ.get("POSTGRES_USER")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD")
POSTGRES_DB = os.environ.get("POSTGRES_DB")

DATABASE_URL = f"postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}"

# Create the asynchronous engine
engine = create_async_engine(DATABASE_URL, echo=True)

# --- 2. Table Creation Function ---
async def create_db_and_tables():
    """Ensures all tables defined in SQLModel metadata are created in the database."""
    print("Attempting to initialize database tables...")
    async with engine.begin() as conn:
        # Runs the synchronous SQLModel.metadata.create_all command within an async context
        
        #must use if any change in schema happens until alembic is used
        #await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)
    print("Database tables initialized successfully.")

# --- Database Dependency ---
async def get_session():
    """Dependency to yield an asynchronous database session for each request."""
    async with AsyncSession(engine) as session:
        yield session

# Type hint for the dependency result, used across the application
SessionDep = Annotated[AsyncSession, Depends(get_session)]
