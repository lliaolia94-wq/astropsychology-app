"""Add users table columns

Revision ID: 002
Revises: 001
Create Date: 2024-11-04 10:45:00.000000

Добавляет все недостающие столбцы в таблицу users:
- phone, password_hash, phone_verified и другие базовые поля
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '002'
# Может быть связана с 001, но если 001 не применена, можно использовать как базовую
down_revision: Union[str, None] = '001'
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
    """Добавляет все недостающие столбцы в таблицу users"""
    
    if not table_exists('users'):
        # Если таблица не существует, создаем её полностью
        op.create_table(
            'users',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('phone', sa.String(length=20), nullable=False),
            sa.Column('password_hash', sa.String(length=255), nullable=False),
            sa.Column('phone_verified', sa.Integer(), nullable=True, server_default='0'),
            sa.Column('name', sa.String(length=100), nullable=True),
            sa.Column('birth_date', sa.String(length=10), nullable=True),
            sa.Column('birth_time', sa.String(length=5), nullable=True),
            sa.Column('birth_place', sa.String(length=200), nullable=True),
            sa.Column('birth_date_detailed', sa.Date(), nullable=True),
            sa.Column('birth_time_detailed', sa.Time(), nullable=True),
            sa.Column('birth_time_utc', sa.DateTime(), nullable=True),
            sa.Column('birth_location_name', sa.String(length=200), nullable=True),
            sa.Column('birth_country', sa.String(length=100), nullable=True),
            sa.Column('birth_latitude', sa.DECIMAL(9, 6), nullable=True),
            sa.Column('birth_longitude', sa.DECIMAL(9, 6), nullable=True),
            sa.Column('timezone_name', sa.String(length=100), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_users_id', 'users', ['id'], unique=False)
        op.create_index('ix_users_phone', 'users', ['phone'], unique=True)
        print("✅ Таблица users создана")
    else:
        # Проверяем, есть ли данные в таблице
        conn = op.get_bind()
        result = conn.execute(sa.text("SELECT COUNT(*) FROM users")).scalar()
        has_data = result > 0
        
        # Добавляем недостающие столбцы
        columns_to_add = [
            # Обязательные поля - сначала добавляем как nullable, если есть данные
            ('phone', sa.String(length=20), False, None),
            ('password_hash', sa.String(length=255), False, None),
            ('phone_verified', sa.Integer(), True, '0'),
            ('name', sa.String(length=100), True, None),
            ('birth_date', sa.String(length=10), True, None),
            ('birth_time', sa.String(length=5), True, None),
            ('birth_place', sa.String(length=200), True, None),
            ('birth_date_detailed', sa.Date(), True, None),
            ('birth_time_detailed', sa.Time(), True, None),
            ('birth_time_utc', sa.DateTime(), True, None),
            ('birth_location_name', sa.String(length=200), True, None),
            ('birth_country', sa.String(length=100), True, None),
            ('birth_latitude', sa.DECIMAL(9, 6), True, None),
            ('birth_longitude', sa.DECIMAL(9, 6), True, None),
            ('timezone_name', sa.String(length=100), True, None),
            ('created_at', sa.DateTime(), True, None),
            ('updated_at', sa.DateTime(), True, None),
        ]
        
        for col_info in columns_to_add:
            col_name = col_info[0]
            col_type = col_info[1]
            nullable = col_info[2]
            default_value = col_info[3] if len(col_info) > 3 else None
            
            if not column_exists('users', col_name):
                # Если таблица содержит данные и столбец NOT NULL, добавляем как nullable временно
                if has_data and not nullable:
                    # Добавляем как nullable, чтобы не было ошибки
                    op.add_column('users', sa.Column(col_name, col_type, nullable=True))
                    print(f"⚠️ Добавлен столбец users.{col_name} как nullable (в таблице есть данные)")
                    print(f"⚠️ ВНИМАНИЕ: Необходимо заполнить данные для столбца {col_name} и сделать его NOT NULL вручную!")
                elif default_value:
                    op.add_column('users', sa.Column(col_name, col_type, nullable=nullable, server_default=str(default_value)))
                    print(f"✅ Добавлен столбец users.{col_name}")
                else:
                    op.add_column('users', sa.Column(col_name, col_type, nullable=nullable))
                    print(f"✅ Добавлен столбец users.{col_name}")
        
        # Создаем индексы, если их нет
        try:
            # Проверяем существование индекса через SQL
            conn = op.get_bind()
            inspector = inspect(conn)
            indexes = [idx['name'] for idx in inspector.get_indexes('users')]
            if 'ix_users_phone' not in indexes:
                op.create_index('ix_users_phone', 'users', ['phone'], unique=True)
                print("✅ Создан индекс ix_users_phone")
        except Exception as e:
            print(f"⚠️ Индекс уже существует или ошибка: {e}")
    
    # Также убеждаемся, что таблица contacts существует
    if not table_exists('contacts'):
        op.create_table(
            'contacts',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('relationship_type', sa.String(length=50), nullable=False),
            sa.Column('custom_title', sa.String(length=100), nullable=True),
            sa.Column('birth_date', sa.String(length=10), nullable=False),
            sa.Column('birth_time', sa.String(length=5), nullable=False),
            sa.Column('birth_place', sa.String(length=200), nullable=False),
            sa.Column('aliases', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_contacts_id', 'contacts', ['id'], unique=False)
        print("✅ Таблица contacts создана")


def downgrade() -> None:
    """Откатывает изменения"""
    # В production не рекомендуется удалять столбцы без резервной копии
    # Здесь мы просто оставляем функцию пустой
    pass

