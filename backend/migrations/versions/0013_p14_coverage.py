"""Additive P14 detection coverage assessments."""
from alembic import op
import sqlalchemy as sa
revision='0013_p14_coverage'
down_revision='0012_p13_simulation'
branch_labels=None
depends_on=None
def upgrade():
    op.create_table('detection_coverage_assessments',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('simulation_run_id',sa.String(36),sa.ForeignKey('lab_simulation_runs.id'),nullable=False),
        sa.Column('rule_id',sa.String(36),sa.ForeignKey('detection_rules.id'),nullable=False),
        sa.Column('event_id',sa.String(36),sa.ForeignKey('telemetry_events.id'),nullable=False),
        sa.Column('finding_id',sa.String(36),sa.ForeignKey('detection_findings.id')),
        sa.Column('outcome',sa.String(24),nullable=False),
        sa.Column('explanation',sa.Text(),nullable=False),
        sa.Column('assessed_by',sa.String(36),sa.ForeignKey('users.id'),nullable=False),
        sa.Column('assessed_at',sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint('simulation_run_id','rule_id',name='uq_p14_run_rule'))
    op.create_index('ix_p14_run','detection_coverage_assessments',['simulation_run_id'])
def downgrade():
    op.drop_index('ix_p14_run',table_name='detection_coverage_assessments')
    op.drop_table('detection_coverage_assessments')
