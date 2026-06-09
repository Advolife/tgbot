from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.db.models import Base

_engine = None
_session_factory = None

def init_engine(database_url: str) -> None:
    global _engine, _session_factory
    _engine = create_async_engine(database_url, pool_pre_ping=True)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)

def get_session_factory():
    if _session_factory is None:
        raise RuntimeError("DB не инициализирована")
    return _session_factory

async def create_all() -> None:
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def dispose() -> None:
    if _engine is not None:
        await _engine.dispose()
