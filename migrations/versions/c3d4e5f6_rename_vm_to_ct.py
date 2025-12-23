"""Rename vm_request table and vm_* columns to ct equivalents

Revision ID: c3d4e5f6
Revises: eb7453a24d50
Create Date: 2025-12-23 00:10:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c3d4e5f6'
down_revision = 'eb7453a24d50'
branch_labels = None
depends_on = None


def upgrade():
    # rename table
    op.rename_table('vm_request', 'ct_request')

    # rename columns
    with op.batch_alter_table('ct_request') as batch_op:
        batch_op.alter_column('vm_ip', new_column_name='ct_ip')
        batch_op.alter_column('vm_hostname', new_column_name='ct_hostname')
        batch_op.alter_column('vm_user', new_column_name='ct_user')
        batch_op.alter_column('vm_password', new_column_name='ct_password')
        batch_op.alter_column('vm_vmid', new_column_name='ct_vmid')


def downgrade():
    with op.batch_alter_table('ct_request') as batch_op:
        batch_op.alter_column('ct_vmid', new_column_name='vm_vmid')
        batch_op.alter_column('ct_password', new_column_name='vm_password')
        batch_op.alter_column('ct_user', new_column_name='vm_user')
        batch_op.alter_column('ct_hostname', new_column_name='vm_hostname')
        batch_op.alter_column('ct_ip', new_column_name='vm_ip')

    op.rename_table('ct_request', 'vm_request')
