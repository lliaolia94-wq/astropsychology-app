"""Add birth_time_utc_offset to users table

Revision ID: 005
Revises: 004
Create Date: 2025-01-05 12:00:00.000000

Добавляет поле birth_time_utc_offset в таблицу users для ручной корректировки UTC offset
при проблемах с определением летнего/зимнего времени.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: Union[str, None] = '004'
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
    """Добавляет поле birth_time_utc_offset в таблицу users"""
    
    if not table_exists('users'):
        print("⚠️ Таблица users не существует, пропускаем миграцию")
        return
    
    if not column_exists('users', 'birth_time_utc_offset'):
        print("Добавление поля birth_time_utc_offset в таблицу users...")
        op.add_column(
            'users',
            sa.Column('birth_time_utc_offset', sa.DECIMAL(5, 2), nullable=True)
        )
        print("✅ birth_time_utc_offset добавлено")
    else:
        print("ℹ️ birth_time_utc_offset уже существует")


def downgrade() -> None:
    """Удаляет поле birth_time_utc_offset из таблицы users"""
    
    if not table_exists('users'):
        print("⚠️ Таблица users не существует, пропускаем откат")
        return
    
    if column_exists('users', 'birth_time_utc_offset'):
        print("Удаление поля birth_time_utc_offset из таблицы users...")
        op.drop_column('users', 'birth_time_utc_offset')
        print("✅ birth_time_utc_offset удалено")
    else:
        print("ℹ️ birth_time_utc_offset не существует")

