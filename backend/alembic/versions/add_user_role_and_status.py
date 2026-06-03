"""add user role and status columns

Revision ID: add_user_role_status
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'add_user_role_status'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add role column with default 'USER'
    op.add_column('users', sa.Column('role', sa.Enum('ADMIN', 'USER', name='userrole'), nullable=False, server_default='USER'))
    # Add status column with default 'PENDING'
    op.add_column('users', sa.Column('status', sa.Enum('PENDING', 'APPROVED', 'REJECTED', name='userstatus'), nullable=False, server_default='PENDING'))


def downgrade() -> None:
    op.drop_column('users', 'status')
    op.drop_column('users', 'role')
    
    # Clean up enum types (PostgreSQL)
    op.execute("DROP TYPE IF EXISTS userstatus")
    op.execute("DROP TYPE IF EXISTS userrole")