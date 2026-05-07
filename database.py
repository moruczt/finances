import os
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from redis import asyncio as aioredis

POSTGRES_URL = os.getenv("POSTGRES_URL")
REDIS_URL = os.getenv("REDIS_URL")

engine = create_async_engine(POSTGRES_URL)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, autoflush=False, expire_on_commit=False, autocommit=False)
redis_pool = aioredis.ConnectionPool.from_url(REDIS_URL, decode_responses=True)

async def get_redis():
    client = aioredis.Redis(connection_pool=redis_pool)
    try:
        yield client
    finally:
        client.close()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session