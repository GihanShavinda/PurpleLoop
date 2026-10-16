"""P10 evidence-grounded analyst report storage. Additive only."""
from alembic import op
import sqlalchemy as sa
revision='0009_p10_analyst'
down_revision='0008_p9_correlation'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('analyst_reports',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('correlation_id',sa.String(36),sa.ForeignKey('correlation_cases.id'),nullable=False),
        sa.Column('asset_id',sa.String(36),sa.ForeignKey('assets.id'),nullable=False),
        sa.Column('created_by',sa.String(36),sa.ForeignKey('users.id'),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('generator_version',sa.String(32),nullable=False),
        sa.Column('report_json',sa.JSON(),nullable=False),
        sa.Column('status',sa.String(24),nullable=False),
        sa.Column('review_note',sa.Text(),nullable=False),
        sa.Column('reviewed_by',sa.String(36),sa.ForeignKey('users.id')),
        sa.Column('reviewed_at',sa.DateTime(timezone=True)))
    op.create_index('ix_p10_reports_correlation','analyst_reports',['correlation_id'])

def downgrade():
    op.drop_index('ix_p10_reports_correlation',table_name='analyst_reports')
    op.drop_table('analyst_reports')
