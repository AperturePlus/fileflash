from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .engine import engine

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)
