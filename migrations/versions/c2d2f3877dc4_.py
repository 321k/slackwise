"""empty message

Revision ID: c2d2f3877dc4
Revises: e49ead68c044
Create Date: 2018-09-21 14:00:33.725780

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c2d2f3877dc4'
down_revision = 'e49ead68c044'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'encrypted_tw_token')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('encrypted_tw_token', sa.VARCHAR(length=240), autoincrement=False, nullable=True))
    # ### end Alembic commands ###
