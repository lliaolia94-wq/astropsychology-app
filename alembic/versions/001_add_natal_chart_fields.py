"""Add natal chart fields

Revision ID: 001
Revises: 
Create Date: 2024-01-01 12:00:00.000000

Добавляет поля:
- users.birth_time_utc
- natal_charts_natalchart.houses_system
- natal_charts_natalchart.zodiac_type
- natal_charts_planetposition.is_retrograde
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Проверяет существование колонки в таблице"""
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def table_exists(table_name: str) -> bool:
    """Проверяет существование таблицы"""
    conn = op.get_bind()
    inspector = inspect(conn)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    # Добавляем birth_time_utc в таблицу users
    if table_exists('users') and not column_exists('users', 'birth_time_utc'):
        op.add_column('users', sa.Column('birth_time_utc', sa.DateTime(), nullable=True))
    
    # Добавляем поля в natal_charts_natalchart
    if table_exists('natal_charts_natalchart'):
        if not column_exists('natal_charts_natalchart', 'houses_system'):
            op.add_column(
                'natal_charts_natalchart',
                sa.Column('houses_system', sa.String(length=20), server_default='placidus', nullable=False)
            )
        if not column_exists('natal_charts_natalchart', 'zodiac_type'):
            op.add_column(
                'natal_charts_natalchart',
                sa.Column('zodiac_type', sa.String(length=10), server_default='tropical', nullable=False)
            )
    
    # Добавляем is_retrograde в natal_charts_planetposition
    if table_exists('natal_charts_planetposition') and not column_exists('natal_charts_planetposition', 'is_retrograde'):
        op.add_column(
            'natal_charts_planetposition',
            sa.Column('is_retrograde', sa.Integer(), server_default='0', nullable=False)
        )


def downgrade() -> None:
    # Откатываем изменения
    if table_exists('natal_charts_planetposition') and column_exists('natal_charts_planetposition', 'is_retrograde'):
        op.drop_column('natal_charts_planetposition', 'is_retrograde')
    
    if table_exists('natal_charts_natalchart'):
        if column_exists('natal_charts_natalchart', 'zodiac_type'):
            op.drop_column('natal_charts_natalchart', 'zodiac_type')
        if column_exists('natal_charts_natalchart', 'houses_system'):
            op.drop_column('natal_charts_natalchart', 'houses_system')
    
    if table_exists('users') and column_exists('users', 'birth_time_utc'):
        op.drop_column('users', 'birth_time_utc')

