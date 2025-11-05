"""Update context system tables

Revision ID: 007
Revises: 006
Create Date: 2025-01-XX XX:XX:XX.XXXXXX

Обновляет систему управления контекстом:
- Добавляет поля в chat_sessions: is_active, parent_session_id, session_type
- Обновляет context_entries: добавляет session_id, новые поля, vector_id
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql, sqlite


# revision identifiers, used by Alembic.
revision: str = '007'
down_revision: Union[str, None] = '006'
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


def is_postgresql() -> bool:
    """Проверяет, используется ли PostgreSQL"""
    conn = op.get_bind()
    return conn.dialect.name == 'postgresql'


def upgrade() -> None:
    """Обновление схемы для системы контекста"""
    
    # ============ Обновление chat_sessions ============
    if table_exists('chat_sessions'):
        # Обновляем title на nullable=False (пока через ALTER если нужно)
        # В SQLite ALTER TABLE ограничен, поэтому пропускаем изменение NOT NULL
        
        # Добавляем is_active
        if not column_exists('chat_sessions', 'is_active'):
            op.add_column('chat_sessions', sa.Column('is_active', sa.Integer(), server_default='1'))
            # Устанавливаем все существующие сессии как активные
            op.execute("UPDATE chat_sessions SET is_active = 1 WHERE is_active IS NULL")
        
        # Добавляем parent_session_id
        if not column_exists('chat_sessions', 'parent_session_id'):
            op.add_column('chat_sessions', sa.Column('parent_session_id', sa.Integer(), nullable=True))
            op.create_foreign_key(
                'fk_chat_sessions_parent',
                'chat_sessions',
                'chat_sessions',
                ['parent_session_id'],
                ['id']
            )
        
        # Добавляем session_type
        if not column_exists('chat_sessions', 'session_type'):
            op.add_column('chat_sessions', sa.Column('session_type', sa.String(50), server_default='regular'))
        
        # Увеличиваем длину title до 500
        if column_exists('chat_sessions', 'title'):
            # В SQLite нельзя изменить тип колонки напрямую
            if is_postgresql():
                op.alter_column('chat_sessions', 'title', type_=sa.String(500), existing_nullable=True)
    
    # ============ Обновление context_entries ============
    if table_exists('context_entries'):
        # Добавляем session_id (обязательное поле)
        if not column_exists('context_entries', 'session_id'):
            # Сначала создаем колонку как nullable
            op.add_column('context_entries', sa.Column('session_id', sa.Integer(), nullable=True))
            
            # Если есть записи, пытаемся связать их с сессиями
            # Для существующих записей создаем связь через user_id (если есть сессии)
            op.execute("""
                UPDATE context_entries 
                SET session_id = (
                    SELECT id FROM chat_sessions 
                    WHERE chat_sessions.user_id = context_entries.user_id 
                    ORDER BY chat_sessions.created_at DESC 
                    LIMIT 1
                )
                WHERE session_id IS NULL
            """)
            
            # Теперь делаем NOT NULL только если все записи имеют session_id
            # В SQLite это сложно, поэтому оставляем nullable для совместимости
            if is_postgresql():
                # Создаем временную сессию для записей без сессии (если такие есть)
                op.execute("""
                    INSERT INTO chat_sessions (user_id, title, created_at, updated_at, is_active, session_type)
                    SELECT DISTINCT user_id, 'Legacy Session', datetime('now'), datetime('now'), 0, 'regular'
                    FROM context_entries
                    WHERE session_id IS NULL
                    ON CONFLICT DO NOTHING
                """)
                
                op.execute("""
                    UPDATE context_entries 
                    SET session_id = (
                        SELECT id FROM chat_sessions 
                        WHERE chat_sessions.user_id = context_entries.user_id 
                        AND chat_sessions.title = 'Legacy Session'
                        LIMIT 1
                    )
                    WHERE session_id IS NULL
                """)
        
        # Добавляем новые поля
        if not column_exists('context_entries', 'user_message'):
            op.add_column('context_entries', sa.Column('user_message', sa.Text(), nullable=True))
        
        if not column_exists('context_entries', 'ai_response'):
            op.add_column('context_entries', sa.Column('ai_response', sa.Text(), nullable=True))
        
        if not column_exists('context_entries', 'emotional_state'):
            op.add_column('context_entries', sa.Column('emotional_state', sa.String(100), nullable=True))
        
        if not column_exists('context_entries', 'event_description'):
            op.add_column('context_entries', sa.Column('event_description', sa.Text(), nullable=True))
        
        if not column_exists('context_entries', 'insight_text'):
            op.add_column('context_entries', sa.Column('insight_text', sa.Text(), nullable=True))
        
        # astro_context: JSONB для PostgreSQL, JSON для SQLite
        if not column_exists('context_entries', 'astro_context'):
            if is_postgresql():
                op.add_column('context_entries', sa.Column('astro_context', postgresql.JSONB, nullable=True))
            else:
                op.add_column('context_entries', sa.Column('astro_context', sa.JSON(), nullable=True))
        
        if not column_exists('context_entries', 'priority'):
            op.add_column('context_entries', sa.Column('priority', sa.Integer(), server_default='1'))
        
        if not column_exists('context_entries', 'entry_type'):
            op.add_column('context_entries', sa.Column('entry_type', sa.String(20), server_default='auto'))
        
        if not column_exists('context_entries', 'vector_id'):
            op.add_column('context_entries', sa.Column('vector_id', sa.String(36), nullable=True))
        
        if not column_exists('context_entries', 'updated_at'):
            op.add_column('context_entries', sa.Column('updated_at', sa.DateTime(), nullable=True))
            # Устанавливаем updated_at = created_at для существующих записей
            op.execute("UPDATE context_entries SET updated_at = created_at WHERE updated_at IS NULL")
        
        # Создаем внешний ключ для session_id (если еще нет)
        # Проверяем существование внешнего ключа
        try:
            if is_postgresql():
                # В PostgreSQL проверяем через information_schema
                result = op.get_bind().execute(sa.text("""
                    SELECT COUNT(*) FROM information_schema.table_constraints 
                    WHERE constraint_name = 'fk_context_entries_session'
                    AND table_name = 'context_entries'
                """))
                if result.scalar() == 0:
                    op.create_foreign_key(
                        'fk_context_entries_session',
                        'context_entries',
                        'chat_sessions',
                        ['session_id'],
                        ['id']
                    )
        except Exception as e:
            print(f"⚠️ Не удалось создать внешний ключ: {e}")


def downgrade() -> None:
    """Откат изменений"""
    
    # Удаляем новые поля из context_entries
    if table_exists('context_entries'):
        columns_to_drop = [
            'vector_id', 'entry_type', 'priority', 'insight_text',
            'event_description', 'emotional_state', 'ai_response',
            'user_message', 'updated_at'
        ]
        
        for col in columns_to_drop:
            if column_exists('context_entries', col):
                op.drop_column('context_entries', col)
        
        # Удаляем astro_context (новый JSONB)
        if column_exists('context_entries', 'astro_context'):
            # Проверяем, не является ли это старым полем Text
            # Если это новый JSONB, удаляем его
            op.drop_column('context_entries', 'astro_context')
        
        # Удаляем session_id (осторожно, может быть данные)
        if column_exists('context_entries', 'session_id'):
            # Удаляем внешний ключ
            try:
                op.drop_constraint('fk_context_entries_session', 'context_entries', type_='foreignkey')
            except:
                pass
            op.drop_column('context_entries', 'session_id')
    
    # Удаляем новые поля из chat_sessions
    if table_exists('chat_sessions'):
        if column_exists('chat_sessions', 'session_type'):
            op.drop_column('chat_sessions', 'session_type')
        
        if column_exists('chat_sessions', 'parent_session_id'):
            try:
                op.drop_constraint('fk_chat_sessions_parent', 'chat_sessions', type_='foreignkey')
            except:
                pass
            op.drop_column('chat_sessions', 'parent_session_id')
        
        if column_exists('chat_sessions', 'is_active'):
            op.drop_column('chat_sessions', 'is_active')

