"""P7 saved hunts and incident event evidence."""
from alembic import op
import sqlalchemy as sa
revision='0006_p7_hunting'
down_revision='0005_p6_incidents'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('saved_hunts',
      sa.Column('id',sa.String(36),primary_key=True),
      sa.Column('name',sa.String(160),nullable=False),
      sa.Column('created_by',sa.String(36),sa.ForeignKey('users.id'),nullable=False),
      sa.Column('filters',sa.JSON(),nullable=False),
      sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))
    op.create_index('ix_saved_hunts_owner','saved_hunts',['created_by','created_at'])
    op.create_table('hunt_evidence',
      sa.Column('id',sa.String(36),primary_key=True),
      sa.Column('case_id',sa.String(36),sa.ForeignKey('incident_cases.id',ondelete='CASCADE'),nullable=False),
      sa.Column('event_id',sa.String(36),sa.ForeignKey('telemetry_events.id'),nullable=False),
      sa.Column('actor_id',sa.String(36),sa.ForeignKey('users.id'),nullable=False),
      sa.Column('note',sa.String(500),nullable=False),
      sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
      sa.UniqueConstraint('case_id','event_id',name='uq_p7_case_event'))
    op.create_index('ix_hunt_evidence_case','hunt_evidence',['case_id'])
    op.create_index('ix_p7_events_type_time','telemetry_events',['event_type','event_time'])

def downgrade():
    op.drop_index('ix_p7_events_type_time',table_name='telemetry_events')
    op.drop_index('ix_hunt_evidence_case',table_name='hunt_evidence')
    op.drop_table('hunt_evidence')
    op.drop_index('ix_saved_hunts_owner',table_name='saved_hunts')
    op.drop_table('saved_hunts')
