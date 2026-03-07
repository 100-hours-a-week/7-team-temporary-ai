from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# 1. SQLAlchemy Async Engine 설정
if not settings.database_url:
    raise ValueError("DATABASE_URL이 설정되지 않았습니다. .env 파일을 확인해주세요.")

DATABASE_URL = settings.database_url

# asyncpg engine 생성
engine = create_async_engine(
    DATABASE_URL,
    echo=settings.debug,
    future=True,
    pool_size=10,
    max_overflow=20
)

# 2. Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# 3. Base class for declarative models (Optional, if using ORM)
Base = declarative_base()

# 4. Dependency for FastAPI
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
