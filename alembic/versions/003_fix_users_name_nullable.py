"""Fix users optional fields to be nullable

Revision ID: 003
Revises: 002
Create Date: 2024-11-04 18:45:00.000000

Исправляет структуру: делает поля name, birth_date, birth_time, birth_place nullable в таблице users
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
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


def upgrade() -> None:
    """Делает поля name, birth_date, birth_time, birth_place nullable в таблице users"""
    
    # Для PostgreSQL
    if op.get_bind().dialect.name == 'postgresql':
        # Поля, которые нужно сделать nullable
        fields_to_fix = [
            ('name', sa.String(length=100)),
            ('birth_date', sa.String(length=10)),
            ('birth_time', sa.String(length=5)),
            ('birth_place', sa.String(length=200))
        ]
        
        for field_name, field_type in fields_to_fix:
            if column_exists('users', field_name):
                # Получаем информацию о текущем столбце
                conn = op.get_bind()
                inspector = inspect(conn)
                columns = inspector.get_columns('users')
                field_col = next((col for col in columns if col['name'] == field_name), None)
                
                if field_col and not field_col['nullable']:
                    # Заменяем пустые строки на NULL для строковых полей
                    if field_name in ['name', 'birth_date', 'birth_time', 'birth_place']:
                        op.execute(f"UPDATE users SET {field_name} = NULL WHERE {field_name} = ''")
                    
                    # Делаем столбец nullable
                    op.alter_column('users', field_name,
                                  existing_type=field_type,
                                  nullable=True)
                    print(f"✅ Столбец users.{field_name} теперь nullable")
    else:
        # Для SQLite - просто проверяем, что столбцы существуют
        for field_name, _ in [('name', None), ('birth_date', None), ('birth_time', None), ('birth_place', None)]:
            if column_exists('users', field_name):
                print(f"✅ Столбец users.{field_name} существует (SQLite не требует явного изменения)")


def downgrade() -> None:
    """Откатывает изменения - делает поля NOT NULL"""
    # Заполняем NULL значения перед установкой NOT NULL
    fields_to_restore = ['name', 'birth_date', 'birth_time', 'birth_place']
    
    for field_name in fields_to_restore:
        if column_exists('users', field_name):
            op.execute(f"UPDATE users SET {field_name} = '' WHERE {field_name} IS NULL")
    
    # Делаем столбцы NOT NULL
    if op.get_bind().dialect.name == 'postgresql':
        op.alter_column('users', 'name',
                      existing_type=sa.String(length=100),
                      nullable=False)
        op.alter_column('users', 'birth_date',
                      existing_type=sa.String(length=10),
                      nullable=False)
        op.alter_column('users', 'birth_time',
                      existing_type=sa.String(length=5),
                      nullable=False)
        op.alter_column('users', 'birth_place',
                      existing_type=sa.String(length=200),
                      nullable=False)

