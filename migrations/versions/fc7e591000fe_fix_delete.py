"""fix delete

Revision ID: fc7e591000fe
Revises: 050587c0910d
Create Date: 2023-07-31 19:14:16.948774

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fc7e591000fe'
down_revision = '050587c0910d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('invitation_id_user_fkey', 'invitation', type_='foreignkey')
    op.create_foreign_key(None, 'invitation', 'user', ['id_user'], ['id'], ondelete='CASCADE')
    op.drop_constraint('request_id_user_fkey', 'request', type_='foreignkey')
    op.create_foreign_key(None, 'request', 'user', ['id_user'], ['id'], ondelete='CASCADE')
    op.drop_constraint('resul_test_id_quiz_fkey', 'resul_test', type_='foreignkey')
    op.create_foreign_key(None, 'resul_test', 'quiz', ['id_quiz'], ['id'], ondelete='CASCADE')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'resul_test', type_='foreignkey')
    op.create_foreign_key('resul_test_id_quiz_fkey', 'resul_test', 'quiz', ['id_quiz'], ['id'])
    op.drop_constraint(None, 'request', type_='foreignkey')
    op.create_foreign_key('request_id_user_fkey', 'request', 'user', ['id_user'], ['id'])
    op.drop_constraint(None, 'invitation', type_='foreignkey')
    op.create_foreign_key('invitation_id_user_fkey', 'invitation', 'user', ['id_user'], ['id'])
    # ### end Alembic commands ###