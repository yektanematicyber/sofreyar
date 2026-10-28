
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.database import Base
from app import models  # Registers SQLAlchemy models with Base.metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Read the database URL from the existing application configuration.
# The app.database module should load DATABASE_URL from .env.
from app.database import engine

config.set_main_option(
    "sqlalchemy.url",
    engine.url.render_as_string(hide_password=False).replace("%", "%%"),
)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
