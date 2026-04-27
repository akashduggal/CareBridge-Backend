import asyncio
import os
from logging.config import fileConfig

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import pool
from alembic import context
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))
#load_dotenv()

# This loads your models so Alembic can detect table changes
from carebridge.app.models.base import Base
from carebridge.app.models import patient, discharge, call, outcome

config = context.config
fileConfig(config.config_file_name)

# Tell Alembic what tables exist (from your models)
target_metadata = Base.metadata

def get_url():
    return os.getenv("DATABASE_URL")

def run_migrations_offline():
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online():
    import ssl
    ssl_context = ssl.create_default_context()
    
    connectable = create_async_engine(
        get_url().split("?")[0],  # strip the ?ssl=require from URL
        poolclass=pool.NullPool,
        connect_args={"ssl": ssl_context}  # pass SSL properly
    )

    #LOCAL CONNECTION 
   # connectable = create_async_engine(
   # get_url(),
   # poolclass=pool.NullPool,
#)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())