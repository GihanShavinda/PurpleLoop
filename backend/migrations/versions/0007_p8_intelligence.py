"""P8 reviewed threat intelligence indicators and matched telemetry."""
from alembic import op
import sqlalchemy as sa
revision='0007_p8_intelligence'
down_revision='0006_p7_hunting'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('intelligence_indicators',
       sa.Column('id',sa.String(36),primary_key=True),
       sa.Column('kind',sa.String(20),nullable=False),
       sa.Column('value',sa.String(255),nullable=False),
       sa.Column('source_label',sa.String(160),nullable=False),
       sa.Column('confidence',sa.Integer(),nullable=False),
       sa.Column('description',sa.Text(),nullable=False),
       sa.Column('enabled',sa.Boolean(),nullable=False),
       sa.Column('created_by',sa.String(36),sa.ForeignKey('users.id'),nullable=False),
       sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
       sa.UniqueConstraint('kind','value',name='uq_p8_indicator_kind_value'))
    op.create_table('intelligence_matches',
       sa.Column('id',sa.String(36),primary_key=True),
       sa.Column('indicator_id',sa.String(36),sa.ForeignKey('intelligence_indicators.id'),nullable=False),
       sa.Column('event_id',sa.String(36),sa.ForeignKey('telemetry_events.id'),nullable=False),
       sa.Column('asset_id',sa.String(36),sa.ForeignKey('assets.id'),nullable=False),
       sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
       sa.UniqueConstraint('indicator_id','event_id',name='uq_p8_indicator_event'))
    op.create_index('ix_p8_matches_indicator','intelligence_matches',['indicator_id'])

def downgrade():
    op.drop_index('ix_p8_matches_indicator',table_name='intelligence_matches')
    op.drop_table('intelligence_matches')
    op.drop_table('intelligence_indicators')
