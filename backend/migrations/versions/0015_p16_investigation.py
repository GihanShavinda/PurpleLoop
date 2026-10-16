"""P16 evidence drafts, additive only."""
from alembic import op
import sqlalchemy as sa
revision='0015_p16_investigation'
down_revision='0014_p15_anomaly'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('investigation_drafts',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('asset_id',sa.String(36),sa.ForeignKey('assets.id'),nullable=False),
        sa.Column('anomaly_run_id',sa.String(36),sa.ForeignKey('anomaly_analysis_runs.id'),nullable=False),
        sa.Column('correlation_id',sa.String(36),sa.ForeignKey('correlation_cases.id')),
        sa.Column('created_by',sa.String(36),sa.ForeignKey('users.id'),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('report_json',sa.JSON(),nullable=False),
        sa.Column('status',sa.String(24),nullable=False),
        sa.Column('review_note',sa.Text(),nullable=False),
        sa.Column('reviewed_by',sa.String(36),sa.ForeignKey('users.id')),
        sa.Column('reviewed_at',sa.DateTime(timezone=True)))
    op.create_index('ix_p16_drafts_run','investigation_drafts',['anomaly_run_id'])

def downgrade():
    op.drop_index('ix_p16_drafts_run',table_name='investigation_drafts')
    op.drop_table('investigation_drafts')
