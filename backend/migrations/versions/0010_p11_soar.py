"""P11 SOAR dry-run proposals and audit. Additive-only migration."""
from alembic import op
import sqlalchemy as sa
revision='0010_p11_soar'
down_revision='0009_p10_analyst'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('soar_proposals',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('playbook_key',sa.String(64),nullable=False),
        sa.Column('incident_id',sa.String(36),sa.ForeignKey('incident_cases.id')),
        sa.Column('correlation_id',sa.String(36),sa.ForeignKey('correlation_cases.id')),
        sa.Column('justification',sa.Text(),nullable=False),
        sa.Column('status',sa.String(24),nullable=False),
        sa.Column('proposed_by',sa.String(36),sa.ForeignKey('users.id'),nullable=False),
        sa.Column('approved_by',sa.String(36),sa.ForeignKey('users.id')),
        sa.Column('decision_note',sa.Text(),nullable=False),
        sa.Column('output_json',sa.JSON()),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('decided_at',sa.DateTime(timezone=True)),
        sa.Column('executed_at',sa.DateTime(timezone=True)))
    op.create_index('ix_p11_status','soar_proposals',['status'])
    op.create_table('soar_audit',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('proposal_id',sa.String(36),sa.ForeignKey('soar_proposals.id',ondelete='CASCADE'),nullable=False),
        sa.Column('actor_id',sa.String(36),sa.ForeignKey('users.id'),nullable=False),
        sa.Column('action',sa.String(32),nullable=False),
        sa.Column('detail',sa.Text(),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))
    op.create_index('ix_p11_audit_proposal','soar_audit',['proposal_id'])
def downgrade():
    op.drop_index('ix_p11_audit_proposal',table_name='soar_audit')
    op.drop_table('soar_audit')
    op.drop_index('ix_p11_status',table_name='soar_proposals')
    op.drop_table('soar_proposals')
