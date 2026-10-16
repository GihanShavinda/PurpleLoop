from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool
from backend.config import get_settings
from backend.database import Base
import backend.models  # noqa: F401
config=context.config
if config.config_file_name is not None:fileConfig(config.config_file_name)
config.set_main_option('sqlalchemy.url',get_settings().database_url.replace('%','%%'))
target_metadata=Base.metadata

def offline():
    context.configure(url=get_settings().database_url,target_metadata=target_metadata,literal_binds=True,dialect_opts={'paramstyle':'named'})
    with context.begin_transaction():context.run_migrations()
def online():
    connectable=engine_from_config(config.get_section(config.config_ini_section,{}),prefix='sqlalchemy.',poolclass=pool.NullPool)
    with connectable.connect() as conn:
        context.configure(connection=conn,target_metadata=target_metadata)
        with context.begin_transaction():context.run_migrations()
if context.is_offline_mode():offline()
else:online()
