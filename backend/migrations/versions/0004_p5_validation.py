"""P5 validation scenarios, runs, and linked detection evidence."""
from alembic import op
import sqlalchemy as sa
revision='0004_p5_validation'
down_revision='0003_p4_detections'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('validation_scenarios',
      sa.Column('id',sa.String(36),primary_key=True),
      sa.Column('name',sa.String(160),nullable=False,unique=True),
      sa.Column('description',sa.Text(),nullable=False),
      sa.Column('rule_id',sa.String(36),sa.ForeignKey('detection_rules.id'),nullable=False),
      sa.Column('asset_id',sa.String(36),sa.ForeignKey('assets.id'),nullable=False),
      sa.Column('technique_id',sa.String(24),nullable=False),
      sa.Column('instructions',sa.Text(),nullable=False),
      sa.Column('enabled',sa.Boolean(),nullable=False),
      sa.Column('created_at',sa.DateTime(timezone=True)))
    op.create_table('validation_runs',
      sa.Column('id',sa.String(36),primary_key=True),
      sa.Column('scenario_id',sa.String(36),sa.ForeignKey('validation_scenarios.id'),nullable=False),
      sa.Column('started_by',sa.String(36),sa.ForeignKey('users.id'),nullable=False),
      sa.Column('started_at',sa.DateTime(timezone=True),nullable=False),
      sa.Column('finished_at',sa.DateTime(timezone=True)),
      sa.Column('status',sa.String(24),nullable=False),
      sa.Column('notes',sa.Text(),nullable=False),
      sa.Column('evidence_count',sa.Integer(),nullable=False))
    op.create_table('validation_evidence',
      sa.Column('id',sa.String(36),primary_key=True),
      sa.Column('run_id',sa.String(36),sa.ForeignKey('validation_runs.id'),nullable=False),
      sa.Column('finding_id',sa.String(36),sa.ForeignKey('detection_findings.id'),nullable=False),
      sa.Column('created_at',sa.DateTime(timezone=True)),
      sa.UniqueConstraint('run_id','finding_id',name='uq_pf_validation_evidence'))

def downgrade():
    op.drop_table('validation_evidence')
    op.drop_table('validation_runs')
    op.drop_table('validation_scenarios')
