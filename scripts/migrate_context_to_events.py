"""
Скрипт для миграции данных из ContextEntry в EventsRegister
"""
import sys
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

# Добавляем корневую директорию в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.database.models import ContextEntry, EventsRegister, User
from app.services.registers_service import registers_service


def categorize_event(context_entry: ContextEntry) -> str:
    """
    Определяет категорию события на основе содержимого
    
    Args:
        context_entry: Запись контекста
        
    Returns:
        Категория события
    """
    # Анализируем теги
    tags = context_entry.tags or []
    tag_str = ' '.join(tags).lower() if isinstance(tags, list) else str(tags).lower()
    
    # Анализируем текст
    text = ' '.join([
        context_entry.user_message or '',
        context_entry.event_description or '',
        context_entry.insight_text or ''
    ]).lower()
    
    # Определяем категорию по ключевым словам
    if any(word in text or word in tag_str for word in ['работа', 'карьер', 'професси', 'бизнес', 'начальник', 'коллега']):
        return 'career'
    elif any(word in text or word in tag_str for word in ['здоров', 'болезн', 'лечен', 'врач', 'боль']):
        return 'health'
    elif any(word in text or word in tag_str for word in ['отношен', 'любов', 'семья', 'партнер', 'друг', 'конфликт']):
        return 'relationships'
    elif any(word in text or word in tag_str for word in ['деньг', 'финанс', 'зарплат', 'покупк', 'трат']):
        return 'finance'
    elif any(word in text or word in tag_str for word in ['духов', 'медитац', 'практик', 'энерг', 'карм']):
        return 'spiritual'
    else:
        return 'general'


def determine_event_type(context_entry: ContextEntry) -> str:
    """
    Определяет тип события
    
    Args:
        context_entry: Запись контекста
        
    Returns:
        Тип события
    """
    if context_entry.user_message and context_entry.ai_response:
        return 'user_message'
    elif context_entry.ai_response:
        return 'ai_response'
    elif context_entry.event_description:
        return 'life_event'
    else:
        return 'general'


def migrate_context_entry(
    db: Session,
    context_entry: ContextEntry,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Мигрирует одну запись ContextEntry в EventsRegister
    
    Args:
        db: Сессия БД
        context_entry: Запись контекста для миграции
        dry_run: Если True, только проверяет без сохранения
        
    Returns:
        Результат миграции
    """
    try:
        # Определяем параметры события
        event_date = context_entry.created_at or datetime.now(timezone.utc)
        effective_from = context_entry.created_at or datetime.now(timezone.utc)
        effective_to = None  # Бессрочно
        
        category = categorize_event(context_entry)
        event_type = determine_event_type(context_entry)
        
        # Проверяем, не существует ли уже такое событие
        existing = db.query(EventsRegister).filter(
            EventsRegister.user_id == context_entry.user_id,
            EventsRegister.session_id == context_entry.session_id,
            EventsRegister.event_date == event_date,
            EventsRegister.user_message == context_entry.user_message
        ).first()
        
        if existing:
            return {
                'status': 'skipped',
                'reason': 'already_exists',
                'event_id': existing.id,
                'context_entry_id': context_entry.id
            }
        
        if dry_run:
            return {
                'status': 'would_create',
                'context_entry_id': context_entry.id,
                'category': category,
                'event_type': event_type
            }
        
        # Создаем событие
        event = registers_service.create_event(
            db=db,
            user_id=context_entry.user_id,
            event_type=event_type,
            category=category,
            event_date=event_date,
            effective_from=effective_from,
            effective_to=effective_to,
            session_id=context_entry.session_id,
            user_message=context_entry.user_message,
            ai_response=context_entry.ai_response,
            emotional_state=context_entry.emotional_state,
            insight_text=context_entry.insight_text,
            event_description=context_entry.event_description,
            astrological_context=context_entry.astro_context,
            tags=context_entry.tags,
            priority=context_entry.priority or 3,
            source='migrated_from_context_entry'
        )
        
        return {
            'status': 'success',
            'context_entry_id': context_entry.id,
            'event_id': event.id,
            'category': category,
            'event_type': event_type
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'context_entry_id': context_entry.id,
            'error': str(e)
        }


def migrate_all_context_entries(
    db: Session,
    user_id: Optional[int] = None,
    dry_run: bool = False,
    limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    Мигрирует все записи ContextEntry в EventsRegister
    
    Args:
        db: Сессия БД
        user_id: Если указан, мигрирует только для этого пользователя
        dry_run: Если True, только проверяет без сохранения
        limit: Максимальное количество записей для миграции
        
    Returns:
        Статистика миграции
    """
    # Получаем записи для миграции
    query = db.query(ContextEntry)
    
    if user_id:
        query = query.filter(ContextEntry.user_id == user_id)
    
    if limit:
        query = query.limit(limit)
    
    context_entries = query.all()
    
    print(f"📊 Найдено записей для миграции: {len(context_entries)}")
    
    if dry_run:
        print("🔍 Режим проверки (dry_run=True) - изменения не будут сохранены")
    
    results = {
        'total': len(context_entries),
        'success': 0,
        'skipped': 0,
        'errors': 0,
        'details': []
    }
    
    for i, entry in enumerate(context_entries, 1):
        if i % 100 == 0:
            print(f"⏳ Обработано: {i}/{len(context_entries)}")
        
        result = migrate_context_entry(db, entry, dry_run=dry_run)
        results['details'].append(result)
        
        if result['status'] == 'success' or result['status'] == 'would_create':
            results['success'] += 1
        elif result['status'] == 'skipped':
            results['skipped'] += 1
        else:
            results['errors'] += 1
    
    if not dry_run:
        db.commit()
        print(f"✅ Миграция завершена. Успешно: {results['success']}, Пропущено: {results['skipped']}, Ошибок: {results['errors']}")
    else:
        print(f"🔍 Проверка завершена. Будет создано: {results['success']}, Пропущено: {results['skipped']}, Ошибок: {results['errors']}")
    
    return results


def main():
    """Главная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Миграция данных из ContextEntry в EventsRegister')
    parser.add_argument('--dry-run', action='store_true', help='Режим проверки без сохранения')
    parser.add_argument('--user-id', type=int, help='Мигрировать только для указанного пользователя')
    parser.add_argument('--limit', type=int, help='Максимальное количество записей')
    
    args = parser.parse_args()
    
    db = SessionLocal()
    try:
        results = migrate_all_context_entries(
            db=db,
            user_id=args.user_id,
            dry_run=args.dry_run,
            limit=args.limit
        )
        
        # Выводим статистику по категориям
        categories = {}
        for detail in results['details']:
            if 'category' in detail:
                cat = detail['category']
                categories[cat] = categories.get(cat, 0) + 1
        
        if categories:
            print("\n📊 Распределение по категориям:")
            for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
                print(f"   {cat}: {count}")
        
    except Exception as e:
        print(f"❌ Ошибка при миграции: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()

