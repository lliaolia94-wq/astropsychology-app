"""increase zodiac_sign length

Revision ID: 004
Revises: 003
Create Date: 2025-11-04 23:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Увеличиваем длину поля zodiac_sign в таблицах PlanetPosition и HouseCuspid
    op.alter_column('natal_charts_planetposition', 'zodiac_sign',
                   existing_type=sa.String(length=10),
                   type_=sa.String(length=20),
                   existing_nullable=False)
    
    op.alter_column('natal_charts_housecuspid', 'zodiac_sign',
                   existing_type=sa.String(length=10),
                   type_=sa.String(length=20),
                   existing_nullable=False)


def downgrade() -> None:
    # Откат изменений
    op.alter_column('natal_charts_planetposition', 'zodiac_sign',
                   existing_type=sa.String(length=20),
                   type_=sa.String(length=10),
                   existing_nullable=False)
    
    op.alter_column('natal_charts_housecuspid', 'zodiac_sign',
                   existing_type=sa.String(length=20),
                   type_=sa.String(length=10),
                   existing_nullable=False)

