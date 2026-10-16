"""P12 rehearsal records. Additive, no live execution."""
from alembic import op
import sqlalchemy as sa
revision='0011_p12_response'
down_revision='0010_p11_soar'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('response_rehearsals',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('proposal_id',sa.String(36),sa.ForeignKey('soar_proposals.id'),nullable=False),
        sa.Column('initiated_by',sa.String(36),sa.ForeignKey('users.id'),nullable=False),
        sa.Column('status',sa.String(24),nullable=False),
        sa.Column('plan_json',sa.JSON(),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('rolled_back_by',sa.String(36),sa.ForeignKey('users.id')),
        sa.Column('rolled_back_at',sa.DateTime(timezone=True)),
        sa.Column('rollback_note',sa.Text(),nullable=False))
    op.create_index('ix_p12_rehearsal_proposal','response_rehearsals',['proposal_id'])
    op.create_table('response_rehearsal_audit',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('rehearsal_id',sa.String(36),sa.ForeignKey('response_rehearsals.id'),nullable=False),
        sa.Column('actor_id',sa.String(36),sa.ForeignKey('users.id'),nullable=False),
        sa.Column('action',sa.String(32),nullable=False),
        sa.Column('note',sa.Text(),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))
    op.create_index('ix_p12_audit_rehearsal','response_rehearsal_audit',['rehearsal_id'])

def downgrade():
    op.drop_index('ix_p12_audit_rehearsal',table_name='response_rehearsal_audit')
    op.drop_table('response_rehearsal_audit')
    op.drop_index('ix_p12_rehearsal_proposal',table_name='response_rehearsals')
    op.drop_table('response_rehearsals')
