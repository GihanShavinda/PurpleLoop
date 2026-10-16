"""P17 operator-reported VMware readiness snapshots, additive only."""
from alembic import op
import sqlalchemy as sa
revision='0016_p17_vmware_range'
down_revision='0015_p16_investigation'
branch_labels=None
depends_on=None
def upgrade():
    op.create_table('vmware_readiness_checks',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('asset_id',sa.String(36),sa.ForeignKey('assets.id'),nullable=False),
        sa.Column('checked_by',sa.String(36),sa.ForeignKey('users.id'),nullable=False),
        sa.Column('checked_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('vmx_path_label',sa.String(400),nullable=False),
        sa.Column('reported_power_state',sa.String(32),nullable=False),
        sa.Column('reported_network',sa.String(100),nullable=False),
        sa.Column('notes',sa.Text(),nullable=False),
        sa.Column('observed_last_event',sa.DateTime(timezone=True)),
        sa.Column('assessment_json',sa.JSON(),nullable=False))
    op.create_index('ix_p17_asset','vmware_readiness_checks',['asset_id'])
def downgrade():
    op.drop_index('ix_p17_asset',table_name='vmware_readiness_checks')
    op.drop_table('vmware_readiness_checks')
