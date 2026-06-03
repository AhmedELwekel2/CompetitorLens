import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Ensure enum types and columns exist (safe for existing tables)
        # This replaces the need for alembic migration for role/status columns
        await conn.execute(sa.text(
            "DO $$ BEGIN "
            "CREATE TYPE userrole AS ENUM ('ADMIN', 'USER'); "
            "EXCEPTION WHEN duplicate_object THEN NULL; "
            "END $$;"
        ))
        await conn.execute(sa.text(
            "DO $$ BEGIN "
            "CREATE TYPE userstatus AS ENUM ('PENDING', 'APPROVED', 'REJECTED'); "
            "EXCEPTION WHEN duplicate_object THEN NULL; "
            "END $$;"
        ))
        # Add role column if missing
        result = await conn.execute(sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name='users' AND column_name='role'"
        ))
        if not result.scalar():
            await conn.execute(sa.text(
                "ALTER TABLE users ADD COLUMN role userrole NOT NULL DEFAULT 'USER'"
            ))
        # Add status column if missing
        result = await conn.execute(sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name='users' AND column_name='status'"
        ))
        if not result.scalar():
            await conn.execute(sa.text(
                "ALTER TABLE users ADD COLUMN status userstatus NOT NULL DEFAULT 'PENDING'"
            ))


async def close_db():
    await engine.dispose()
