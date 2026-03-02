import asyncio

from app.db.base import Base
from app.db.session import engine
import app.db.models  # важно: чтобы модели зарегистрировались в metadata


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await engine.dispose()
    print("Tables created")


if __name__ == "__main__":
    asyncio.run(main())