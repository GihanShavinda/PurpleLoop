"""P6 incident cases and linked findings. Additive only."""
from alembic import op
import sqlalchemy as sa
revision='0005_p6_incidents'
down_revision='0004_p5_validation'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('incident_cases',
      sa.Column('id',sa.String(36),primary_key=True),
      sa.Column('title',sa.String(180),nullable=False),
      sa.Column('description',sa.Text(),nullable=False),
      sa.Column('asset_id',sa.String(36),sa.ForeignKey('assets.id'),nullable=False),
      sa.Column('severity',sa.String(20),nullable=False),
      sa.Column('status',sa.String(24),nullable=False),
      sa.Column('assignee_id',sa.String(36),sa.ForeignKey('users.id')),
      sa.Column('created_by',sa.String(36),sa.ForeignKey('users.id'),nullable=False),
      sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
      sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False))
    op.create_index('ix_incident_cases_asset', 'incident_cases',['asset_id'])
    op.create_table('incident_findings',
      sa.Column('id',sa.String(36),primary_key=True),
      sa.Column('case_id',sa.String(36),sa.ForeignKey('incident_cases.id',ondelete='CASCADE'),nullable=False),
      sa.Column('finding_id',sa.String(36),sa.ForeignKey('detection_findings.id'),nullable=False,unique=True),
      sa.Column('linked_at',sa.DateTime(timezone=True),nullable=False))
    op.create_index('ix_incident_findings_case','incident_findings',['case_id'])
    op.create_table('incident_notes',
      sa.Column('id',sa.String(36),primary_key=True),
      sa.Column('case_id',sa.String(36),sa.ForeignKey('incident_cases.id',ondelete='CASCADE'),nullable=False),
      sa.Column('actor_id',sa.String(36),sa.ForeignKey('users.id'),nullable=False),
      sa.Column('note',sa.Text(),nullable=False),
      sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))
    op.create_index('ix_incident_notes_case','incident_notes',['case_id'])

def downgrade():
    op.drop_index('ix_incident_notes_case',table_name='incident_notes')
    op.drop_table('incident_notes')
    op.drop_index('ix_incident_findings_case',table_name='incident_findings')
    op.drop_table('incident_findings')
    op.drop_index('ix_incident_cases_asset',table_name='incident_cases')
    op.drop_table('incident_cases')
