from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from .config import settings

# Async engine for FastAPI routes
async_engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

# Sync engine for Authlib OAuth2 callbacks (AuthorizationServer is synchronous)
sync_url = settings.database_url.replace("sqlite+aiosqlite:///", "sqlite:///")
sync_engine = create_engine(sync_url, echo=False)


async def init_db():
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
