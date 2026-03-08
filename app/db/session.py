from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings

if not settings.database_url:
    # Fallback or error if DATABASE_URL is missing
    # In some cases, we might still want to use Supabase client, 
    # but for direct DB operations, we need this.
    pass

engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    echo=False, # Set to True for debugging SQL
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database sessions.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
