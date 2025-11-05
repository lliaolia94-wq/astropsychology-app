"""Add current location fields to users table

Revision ID: 006
Revises: 005
Create Date: 2025-01-05 14:00:00.000000

Добавляет поля текущего местоположения пользователя для расчета транзитов:
- current_location_name
- current_country
- current_latitude
- current_longitude
- current_timezone_name
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Проверяет существование колонки в таблице"""
    conn = op.get_bind()
    inspector = inspect(conn)
    if not inspector.has_table(table_name):
        return False
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def table_exists(table_name: str) -> bool:
    """Проверяет существование таблицы"""
    conn = op.get_bind()
    inspector = inspect(conn)
    return inspector.has_table(table_name)


def upgrade() -> None:
    """Добавляет поля текущего местоположения в таблицу users"""
    
    if not table_exists('users'):
        print("⚠️ Таблица users не существует, пропускаем миграцию")
        return
    
    columns_to_add = [
        ('current_location_name', sa.String(200), None),
        ('current_country', sa.String(100), None),
        ('current_latitude', sa.DECIMAL(9, 6), None),
        ('current_longitude', sa.DECIMAL(9, 6), None),
        ('current_timezone_name', sa.String(100), None),
    ]
    
    for column_name, column_type, default_value in columns_to_add:
        if not column_exists('users', column_name):
            print(f"Добавление поля {column_name} в таблицу users...")
            op.add_column('users', sa.Column(column_name, column_type, nullable=True))
            print(f"✅ {column_name} добавлено")
        else:
            print(f"ℹ️ {column_name} уже существует")


def downgrade() -> None:
    """Удаляет поля текущего местоположения из таблицы users"""
    
    if not table_exists('users'):
        print("⚠️ Таблица users не существует, пропускаем откат")
        return
    
    columns_to_remove = [
        'current_timezone_name',
        'current_longitude',
        'current_latitude',
        'current_country',
        'current_location_name',
    ]
    
    for column_name in columns_to_remove:
        if column_exists('users', column_name):
            print(f"Удаление поля {column_name} из таблицы users...")
            op.drop_column('users', column_name)
            print(f"✅ {column_name} удалено")
        else:
            print(f"ℹ️ {column_name} не существует")
