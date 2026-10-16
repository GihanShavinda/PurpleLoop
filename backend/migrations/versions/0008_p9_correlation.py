"""P9 additive correlation schema."""
from alembic import op
import sqlalchemy as sa
revision='0008_p9_correlation'
down_revision='0007_p8_intelligence'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('correlation_cases',
      sa.Column('id',sa.String(36),primary_key=True),
      sa.Column('asset_id',sa.String(36),sa.ForeignKey('assets.id'),nullable=False),
      sa.Column('window_start',sa.DateTime(timezone=True),nullable=False),
      sa.Column('window_end',sa.DateTime(timezone=True),nullable=False),
      sa.Column('risk_score',sa.Integer(),nullable=False),
      sa.Column('risk_reasons',sa.JSON(),nullable=False),
      sa.Column('finding_count',sa.Integer(),nullable=False),
      sa.Column('indicator_count',sa.Integer(),nullable=False),
      sa.Column('status',sa.String(24),nullable=False),
      sa.Column('created_by',sa.String(36),sa.ForeignKey('users.id'),nullable=False),
      sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
      sa.UniqueConstraint('asset_id','window_start','window_end',name='uq_p9_asset_window'))
    op.create_index('ix_p9_cases_asset','correlation_cases',['asset_id'])
    op.create_table('correlation_evidence',
      sa.Column('id',sa.String(36),primary_key=True),
      sa.Column('correlation_id',sa.String(36),sa.ForeignKey('correlation_cases.id',ondelete='CASCADE'),nullable=False),
      sa.Column('event_id',sa.String(36),sa.ForeignKey('telemetry_events.id'),nullable=False),
      sa.Column('finding_id',sa.String(36),sa.ForeignKey('detection_findings.id')),
      sa.Column('intelligence_match_id',sa.String(36),sa.ForeignKey('intelligence_matches.id')),
      sa.Column('evidence_kind',sa.String(20),nullable=False),
      sa.UniqueConstraint('correlation_id','evidence_kind','event_id',name='uq_p9_case_kind_event'))
    op.create_index('ix_p9_evidence_case','correlation_evidence',['correlation_id'])

def downgrade():
    op.drop_index('ix_p9_evidence_case',table_name='correlation_evidence')
    op.drop_table('correlation_evidence')
    op.drop_index('ix_p9_cases_asset',table_name='correlation_cases')
    op.drop_table('correlation_cases')
