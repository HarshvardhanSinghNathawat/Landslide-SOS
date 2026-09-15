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
    op.add_column('alerts', sa.Column('triggered_by', sa.Integer(), nullable=True))
    op.add_column('alerts', sa.Column('sms_failed', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('alerts', sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key('fk_alerts_triggered_by', 'alerts', 'users', ['triggered_by'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_alerts_triggered_by', 'alerts', type_='foreignkey')
    op.drop_column('alerts', 'sent_at')
    op.drop_column('alerts', 'sms_failed')
    op.drop_column('alerts', 'triggered_by')
