"""P13 authorized manual lab simulations; additive migration."""
from alembic import op
import sqlalchemy as sa
revision='0012_p13_simulation'
down_revision='0011_p12_response'
branch_labels=None
depends_on=None
def upgrade():
    op.create_table('lab_simulation_runs',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('asset_id',sa.String(36),sa.ForeignKey('assets.id'),nullable=False),
        sa.Column('scenario_key',sa.String(64),nullable=False),
        sa.Column('marker',sa.String(100),nullable=False,unique=True),
        sa.Column('status',sa.String(24),nullable=False),
        sa.Column('initiated_by',sa.String(36),sa.ForeignKey('users.id'),nullable=False),
        sa.Column('started_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('ended_at',sa.DateTime(timezone=True)),
        sa.Column('evidence_event_id',sa.String(36),sa.ForeignKey('telemetry_events.id')),
        sa.Column('note',sa.Text(),nullable=False))
    op.create_index('ix_p13_runs_asset','lab_simulation_runs',['asset_id'])
    op.create_index('ix_p13_runs_started','lab_simulation_runs',['started_at'])
def downgrade():
    op.drop_index('ix_p13_runs_started',table_name='lab_simulation_runs')
    op.drop_index('ix_p13_runs_asset',table_name='lab_simulation_runs')
    op.drop_table('lab_simulation_runs')
