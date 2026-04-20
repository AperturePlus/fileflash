from .engine import engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)
