"""P4 detection rules and findings, additive and non-destructive."""
from alembic import op
from sqlalchemy import inspect
import sqlalchemy as sa
revision='0003_p4_detections'
down_revision='0002_p3_telemetry'
branch_labels=None
depends_on=None

def upgrade():
    tables=set(inspect(op.get_bind()).get_table_names())
    if 'detection_rules' not in tables:
        op.create_table('detection_rules',
            sa.Column('id',sa.String(36),primary_key=True),sa.Column('name',sa.String(160),nullable=False,unique=True),
            sa.Column('rule_kind',sa.String(24),nullable=False),sa.Column('description',sa.Text(),nullable=False),
            sa.Column('severity',sa.String(20),nullable=False),sa.Column('enabled',sa.Boolean(),nullable=False),
            sa.Column('event_type',sa.String(120)),sa.Column('field_name',sa.String(160),nullable=False),
            sa.Column('operator',sa.String(24),nullable=False),sa.Column('expected_value',sa.String(512),nullable=False),
            sa.Column('mitre_attack',sa.String(32)),sa.Column('created_at',sa.DateTime(timezone=True)))
    if 'detection_findings' not in tables:
        op.create_table('detection_findings',
            sa.Column('id',sa.String(36),primary_key=True),
            sa.Column('rule_id',sa.String(36),sa.ForeignKey('detection_rules.id'),nullable=False),
            sa.Column('event_id',sa.String(36),sa.ForeignKey('telemetry_events.id'),nullable=False),
            sa.Column('asset_id',sa.String(36),sa.ForeignKey('assets.id'),nullable=False),
            sa.Column('severity',sa.String(20),nullable=False),sa.Column('status',sa.String(24),nullable=False),
            sa.Column('created_at',sa.DateTime(timezone=True)),
            sa.UniqueConstraint('rule_id','event_id',name='uq_pf_detection_rule_event'))

def downgrade():
    op.drop_table('detection_findings')
    op.drop_table('detection_rules')
