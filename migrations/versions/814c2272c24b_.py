"""empty message

Revision ID: 814c2272c24b
Revises: 556d018eeecf
Create Date: 2018-09-11 18:03:49.772475

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '814c2272c24b'
down_revision = '556d018eeecf'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('encryped_tw_token', sa.String(length=240), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'encryped_tw_token')
    # ### end Alembic commands ###
