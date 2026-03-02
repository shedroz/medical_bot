import os
from dotenv import load_dotenv

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "medical_bot")
DB_USER = os.getenv("DB_USER", "botuser")
DB_PASSWORD = os.getenv("DB_PASSWORD", "botpass")

DATABASE_URL = (
    f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

engine = create_async_engine(DATABASE_URL, echo=False)
SessionMaker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)