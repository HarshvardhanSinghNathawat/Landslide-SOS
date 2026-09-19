"""phase 3 alert sms columns

Revision ID: 99f87406c0b8
Revises: abd075c89bd9
Create Date: 2026-09-15 19:12:13.372767

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '99f87406c0b8'
down_revision: Union[str, Sequence[str], None] = 'abd075c89bd9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('alerts') as batch_op:
        batch_op.add_column(sa.Column('triggered_by', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('sms_failed', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.create_foreign_key('fk_alerts_triggered_by', 'users', ['triggered_by'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('alerts') as batch_op:
        batch_op.drop_constraint('fk_alerts_triggered_by', type_='foreignkey')
        batch_op.drop_column('sent_at')
        batch_op.drop_column('sms_failed')
        batch_op.drop_column('triggered_by')
