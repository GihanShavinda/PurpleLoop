"""P3 collector credentials and normalized telemetry events.

Revision ID: 0002_p3_telemetry
Revises: 0001_initial
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
revision='0002_p3_telemetry'
down_revision='0001_initial'
branch_labels=None
depends_on=None

def upgrade():
    existing={c['name'] for c in inspect(op.get_bind()).get_columns('telemetry_sources')}
    if 'name' not in existing: op.add_column('telemetry_sources', sa.Column('name',sa.String(150),nullable=True))
    if 'token_sha256' not in existing: op.add_column('telemetry_sources', sa.Column('token_sha256',sa.String(64),nullable=True))
    if 'last_seen_at' not in existing: op.add_column('telemetry_sources', sa.Column('last_seen_at',sa.DateTime(timezone=True),nullable=True))
    if 'created_at' not in existing: op.add_column('telemetry_sources', sa.Column('created_at',sa.DateTime(timezone=True),nullable=True))
    constraints={c['name'] for c in inspect(op.get_bind()).get_unique_constraints('telemetry_sources')}
    if 'uq_telemetry_sources_token_sha256' not in constraints and 'ix_telemetry_sources_token_sha256' not in {i['name'] for i in inspect(op.get_bind()).get_indexes('telemetry_sources')}:
        op.create_unique_constraint('uq_telemetry_sources_token_sha256','telemetry_sources',['token_sha256'])
    if 'telemetry_events' not in inspect(op.get_bind()).get_table_names():
      op.create_table('telemetry_events',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('source_id',sa.String(36),sa.ForeignKey('telemetry_sources.id',ondelete='CASCADE'),nullable=False),
        sa.Column('asset_id',sa.String(36),sa.ForeignKey('assets.id',ondelete='CASCADE'),nullable=False),
        sa.Column('event_time',sa.DateTime(timezone=True),nullable=False),
        sa.Column('received_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('event_type',sa.String(120),nullable=False),
        sa.Column('severity',sa.String(20),nullable=False),
        sa.Column('message',sa.Text(),nullable=False),
        sa.Column('payload',sa.JSON(),nullable=False))
    existing_indexes={i['name'] for i in inspect(op.get_bind()).get_indexes('telemetry_events')}
    if 'ix_telemetry_events_source_id' not in existing_indexes:op.create_index('ix_telemetry_events_source_id','telemetry_events',['source_id'])
    if 'ix_telemetry_events_asset_id' not in existing_indexes:op.create_index('ix_telemetry_events_asset_id','telemetry_events',['asset_id'])
    if 'ix_telemetry_events_event_time' not in existing_indexes:op.create_index('ix_telemetry_events_event_time','telemetry_events',['event_time'])
    if 'ix_pf_events_asset_time' not in existing_indexes:op.create_index('ix_pf_events_asset_time','telemetry_events',['asset_id','event_time'])

def downgrade():
    op.drop_table('telemetry_events')
    op.drop_constraint('uq_telemetry_sources_token_sha256','telemetry_sources',type_='unique')
    for col in ('created_at','last_seen_at','token_sha256','name'):
        op.drop_column('telemetry_sources',col)
