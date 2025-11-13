"""Add registers tables for context information

Revision ID: 008
Revises: 007
Create Date: 2025-01-XX XX:XX:XX.XXXXXX

Создает таблицы регистров для контекстной информации:
- events_register: основной регистр событий
- contacts_register: регистр контактов с астрологическими данными
- transits_register: регистр транзитов
- virtual_slices: регистр виртуальных срезов
- karmic_themes_register: регистр кармических тем
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql, sqlite
from datetime import datetime, timezone


# revision identifiers, used by Alembic.
revision: str = '008'
down_revision: Union[str, None] = '007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


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
    """Создание таблиц регистров"""
    
    # Определяем тип JSON для текущей БД
    json_type = postgresql.JSONB if is_postgresql() else sa.JSON
    
    # ============ EVENTS_REGISTER ============
    if not table_exists('events_register'):
        op.create_table(
            'events_register',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('session_id', sa.Integer(), nullable=True),
            
            # Временные метки
            sa.Column('event_date', sa.DateTime(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('effective_from', sa.DateTime(), nullable=False),
            sa.Column('effective_to', sa.DateTime(), nullable=True),
            
            # Классификация
            sa.Column('event_type', sa.String(50), nullable=False),
            sa.Column('category', sa.String(50), nullable=False),
            sa.Column('priority', sa.Integer(), server_default='3'),
            
            # Содержимое
            sa.Column('title', sa.String(500), nullable=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('user_message', sa.Text(), nullable=True),
            sa.Column('ai_response', sa.Text(), nullable=True),
            sa.Column('insight_text', sa.Text(), nullable=True),
            
            # Эмоциональный контекст
            sa.Column('emotional_state', sa.String(50), nullable=True),
            sa.Column('emotional_intensity', sa.DECIMAL(3, 2), nullable=True),
            sa.Column('emotional_trigger', sa.String(200), nullable=True),
            
            # Астрологический контекст
            sa.Column('astrological_context', json_type, nullable=True),
            sa.Column('natal_chart_snapshot_id', sa.Integer(), nullable=True),
            
            # Метаданные
            sa.Column('tags', sa.JSON(), nullable=True),
            sa.Column('source', sa.String(100), nullable=True),
            sa.Column('confidence_score', sa.DECIMAL(3, 2), server_default='1.0'),
            
            # Ссылки на связанные сущности
            sa.Column('contact_ids', sa.JSON(), nullable=True),
            sa.Column('location_id', sa.Integer(), nullable=True),
            sa.Column('business_context_id', sa.Integer(), nullable=True),
            
            sa.PrimaryKeyConstraint('id')
        )
        
        # Внешние ключи
        op.create_foreign_key(
            'fk_events_register_user',
            'events_register', 'users',
            ['user_id'], ['id']
        )
        op.create_foreign_key(
            'fk_events_register_session',
            'events_register', 'chat_sessions',
            ['session_id'], ['id']
        )
        op.create_foreign_key(
            'fk_events_register_natal_chart',
            'events_register', 'natal_charts_natalchart',
            ['natal_chart_snapshot_id'], ['id']
        )
        
        # Индексы для events_register
        op.create_index('idx_events_user_date', 'events_register', ['user_id', 'event_date'])
        op.create_index('idx_events_type_category', 'events_register', ['event_type', 'category'])
        op.create_index('idx_events_emotional', 'events_register', ['user_id', 'emotional_state'])
        op.create_index('idx_events_effective', 'events_register', ['user_id', 'effective_from', 'effective_to'])
        print("✅ Создана таблица events_register")
    
    # ============ CONTACTS_REGISTER ============
    if not table_exists('contacts_register'):
        op.create_table(
            'contacts_register',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            
            # Основная информация
            sa.Column('name', sa.String(200), nullable=False),
            sa.Column('relationship_type', sa.String(50), nullable=False),
            sa.Column('relationship_depth', sa.Integer(), nullable=True),
            
            # Астрологические данные
            sa.Column('birth_date', sa.Date(), nullable=True),
            sa.Column('birth_time', sa.Time(), nullable=True),
            sa.Column('birth_place', sa.String(300), nullable=True),
            sa.Column('timezone', sa.String(50), nullable=True),
            
            # Рассчитанные данные
            sa.Column('natal_chart_data', json_type, nullable=True),
            sa.Column('synastry_with_user', json_type, nullable=True),
            sa.Column('composite_chart', json_type, nullable=True),
            
            # Динамика отношений
            sa.Column('interaction_frequency', sa.String(20), nullable=True),
            sa.Column('last_interaction_date', sa.DateTime(), nullable=True),
            sa.Column('emotional_pattern', json_type, nullable=True),
            
            # Метаданные
            sa.Column('tags', sa.JSON(), nullable=True),
            sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False),
            sa.Column('privacy_level', sa.String(20), server_default='private', nullable=False),
            
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            
            sa.PrimaryKeyConstraint('id')
        )
        
        # Внешний ключ
        op.create_foreign_key(
            'fk_contacts_register_user',
            'contacts_register', 'users',
            ['user_id'], ['id']
        )
        
        # Индексы для contacts_register
        op.create_index('idx_contacts_user', 'contacts_register', ['user_id'])
        op.create_index('idx_contacts_relationship', 'contacts_register', ['user_id', 'relationship_type'])
        op.create_index('idx_contacts_active', 'contacts_register', ['user_id', 'is_active'])
        print("✅ Создана таблица contacts_register")
    
    # ============ TRANSITS_REGISTER ============
    if not table_exists('transits_register'):
        op.create_table(
            'transits_register',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            
            # Период действия
            sa.Column('calculation_date', sa.Date(), nullable=False),
            sa.Column('start_date', sa.Date(), nullable=False),
            sa.Column('end_date', sa.Date(), nullable=False),
            sa.Column('transit_date', sa.Date(), nullable=False),
            
            # Астрологические данные
            sa.Column('transit_type', sa.String(50), nullable=False),
            sa.Column('planet_from', sa.String(20), nullable=False),
            sa.Column('planet_to', sa.String(20), nullable=True),
            sa.Column('aspect_type', sa.String(20), nullable=True),
            sa.Column('exact_time', sa.DateTime(), nullable=True),
            
            # Астрологические параметры
            sa.Column('orb', sa.DECIMAL(4, 2), nullable=True),
            sa.Column('strength', sa.DECIMAL(3, 2), nullable=True),
            sa.Column('house', sa.Integer(), nullable=True),
            
            # Интерпретация
            sa.Column('interpretation', sa.Text(), nullable=True),
            sa.Column('impact_level', sa.String(20), nullable=False),
            sa.Column('impact_areas', sa.JSON(), nullable=True),
            
            # Связи
            sa.Column('related_transit_ids', sa.JSON(), nullable=True),
            sa.Column('triggered_event_ids', sa.JSON(), nullable=True),
            
            sa.Column('created_at', sa.DateTime(), nullable=False),
            
            sa.PrimaryKeyConstraint('id')
        )
        
        # Внешний ключ
        op.create_foreign_key(
            'fk_transits_register_user',
            'transits_register', 'users',
            ['user_id'], ['id']
        )
        
        # Индексы для transits_register
        op.create_index('idx_transits_user_period', 'transits_register', ['user_id', 'start_date', 'end_date'])
        op.create_index('idx_transits_date', 'transits_register', ['user_id', 'transit_date'])
        op.create_index('idx_transits_planet', 'transits_register', ['user_id', 'planet_from', 'planet_to'])
        op.create_index('idx_transits_impact', 'transits_register', ['user_id', 'impact_level'])
        print("✅ Создана таблица transits_register")
    
    # ============ VIRTUAL_SLICES ============
    if not table_exists('virtual_slices'):
        op.create_table(
            'virtual_slices',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('slice_name', sa.String(100), nullable=False),
            
            # Параметры среза
            sa.Column('slice_type', sa.String(50), nullable=False),
            sa.Column('date_from', sa.DateTime(), nullable=True),
            sa.Column('date_to', sa.DateTime(), nullable=True),
            sa.Column('filters', json_type, nullable=False),
            
            # Результаты среза (кэш)
            sa.Column('included_event_ids', sa.JSON(), nullable=True),
            sa.Column('included_contact_ids', sa.JSON(), nullable=True),
            sa.Column('included_transit_ids', sa.JSON(), nullable=True),
            
            # Статистика среза
            sa.Column('events_count', sa.Integer(), server_default='0', nullable=False),
            sa.Column('patterns_detected', json_type, nullable=True),
            sa.Column('summary_statistics', json_type, nullable=True),
            
            # Метаданные
            sa.Column('is_cached', sa.Boolean(), server_default='0', nullable=False),
            sa.Column('cache_ttl_hours', sa.Integer(), server_default='24', nullable=False),
            sa.Column('last_accessed', sa.DateTime(), nullable=False),
            
            sa.Column('created_at', sa.DateTime(), nullable=False),
            
            sa.PrimaryKeyConstraint('id')
        )
        
        # Внешний ключ
        op.create_foreign_key(
            'fk_virtual_slices_user',
            'virtual_slices', 'users',
            ['user_id'], ['id']
        )
        
        # Индексы для virtual_slices
        op.create_index('idx_slices_user', 'virtual_slices', ['user_id'])
        op.create_index('idx_slices_type', 'virtual_slices', ['user_id', 'slice_type'])
        op.create_index('idx_slices_date', 'virtual_slices', ['user_id', 'date_from', 'date_to'])
        op.create_index('idx_slices_access', 'virtual_slices', ['user_id', 'last_accessed'])
        print("✅ Создана таблица virtual_slices")
    
    # ============ KARMIC_THEMES_REGISTER ============
    if not table_exists('karmic_themes_register'):
        op.create_table(
            'karmic_themes_register',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            
            # Идентификация темы
            sa.Column('theme_name', sa.String(100), nullable=False),
            sa.Column('theme_type', sa.String(50), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            
            # Астрологические индикаторы
            sa.Column('natal_indicators', json_type, nullable=True),
            sa.Column('transit_indicators', json_type, nullable=True),
            
            # Проявление в жизни
            sa.Column('manifestation_level', sa.DECIMAL(3, 2), nullable=True),
            sa.Column('first_manifested_date', sa.DateTime(), nullable=True),
            sa.Column('last_manifested_date', sa.DateTime(), nullable=True),
            sa.Column('manifestation_count', sa.Integer(), server_default='0', nullable=False),
            
            # Связанные события и контакты
            sa.Column('related_event_ids', sa.JSON(), nullable=True),
            sa.Column('related_contact_ids', sa.JSON(), nullable=True),
            sa.Column('triggering_transit_ids', sa.JSON(), nullable=True),
            
            # Статус и приоритет
            sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False),
            sa.Column('resolution_status', sa.String(20), server_default='unresolved', nullable=False),
            sa.Column('priority', sa.Integer(), nullable=True),
            
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            
            sa.PrimaryKeyConstraint('id')
        )
        
        # Внешний ключ
        op.create_foreign_key(
            'fk_karmic_themes_register_user',
            'karmic_themes_register', 'users',
            ['user_id'], ['id']
        )
        
        # Индексы для karmic_themes_register
        op.create_index('idx_themes_user', 'karmic_themes_register', ['user_id'])
        op.create_index('idx_themes_active', 'karmic_themes_register', ['user_id', 'is_active'])
        op.create_index('idx_themes_resolution', 'karmic_themes_register', ['user_id', 'resolution_status'])
        print("✅ Создана таблица karmic_themes_register")


def downgrade() -> None:
    """Откат изменений - удаление таблиц регистров"""
    
    # Удаляем таблицы в обратном порядке (из-за внешних ключей)
    tables_to_drop = [
        'karmic_themes_register',
        'virtual_slices',
        'transits_register',
        'contacts_register',
        'events_register'
    ]
    
    for table_name in tables_to_drop:
        if table_exists(table_name):
            op.drop_table(table_name)
            print(f"✅ Удалена таблица {table_name}")

