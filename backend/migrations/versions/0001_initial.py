"""P1 initial schema.

Revision ID: 0001_initial
Revises:
"""
from alembic import op
from backend.database import Base
import backend.models  # noqa: F401
revision='0001_initial'
down_revision=None
branch_labels=None
depends_on=None

def upgrade():
    connection = op.get_bind()
    for table in Base.metadata.sorted_tables:
        table.create(bind=connection)

def downgrade():
    connection = op.get_bind()
    for table in reversed(Base.metadata.sorted_tables):
        table.drop(bind=connection)
