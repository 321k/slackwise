"""empty message

Revision ID: 32e8153cef61
Revises: a4a301d2c293
Create Date: 2018-09-21 14:02:57.394826

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '32e8153cef61'
down_revision = 'a4a301d2c293'
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
