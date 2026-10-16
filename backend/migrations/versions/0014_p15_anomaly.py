"""P15 additive anomaly analysis snapshots."""
from alembic import op
import sqlalchemy as sa
revision='0014_p15_anomaly'
down_revision='0013_p14_coverage'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('anomaly_analysis_runs',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('asset_id',sa.String(36),sa.ForeignKey('assets.id'),nullable=False),
        sa.Column('initiated_by',sa.String(36),sa.ForeignKey('users.id'),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('window_start',sa.DateTime(timezone=True),nullable=False),
        sa.Column('window_end',sa.DateTime(timezone=True),nullable=False),
        sa.Column('bucket_minutes',sa.Integer(),nullable=False),
        sa.Column('event_count',sa.Integer(),nullable=False),
        sa.Column('bucket_count',sa.Integer(),nullable=False),
        sa.Column('anomaly_count',sa.Integer(),nullable=False),
        sa.Column('parameters_json',sa.JSON(),nullable=False),
        sa.Column('status',sa.String(24),nullable=False))
    op.create_index('ix_p15_runs_asset','anomaly_analysis_runs',['asset_id'])
    op.create_table('anomaly_observations',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('run_id',sa.String(36),sa.ForeignKey('anomaly_analysis_runs.id',ondelete='CASCADE'),nullable=False),
        sa.Column('bucket_start',sa.DateTime(timezone=True),nullable=False),
        sa.Column('anomaly_score',sa.Float(),nullable=False),
        sa.Column('event_count',sa.Integer(),nullable=False),
        sa.Column('explanation_json',sa.JSON(),nullable=False),
        sa.UniqueConstraint('run_id','bucket_start',name='uq_p15_run_bucket'))
    op.create_index('ix_p15_obs_run','anomaly_observations',['run_id'])

def downgrade():
    op.drop_index('ix_p15_obs_run',table_name='anomaly_observations')
    op.drop_table('anomaly_observations')
    op.drop_index('ix_p15_runs_asset',table_name='anomaly_analysis_runs')
    op.drop_table('anomaly_analysis_runs')
