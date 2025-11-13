"""
Скрипт для миграции данных из старой таблицы contacts в contacts_register
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
from app.models.database.models import Contact, ContactsRegister, User
from app.services.registers_service import registers_service


def parse_date(date_str: str) -> Optional[datetime.date]:
    """Парсит дату из строки"""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def parse_time(time_str: str) -> Optional[datetime.time]:
    """Парсит время из строки"""
    if not time_str:
        return None
    try:
        return datetime.strptime(time_str, "%H:%M").time()
    except (ValueError, TypeError):
        return None


def migrate_contact(
    db: Session,
    old_contact: Contact,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Мигрирует один контакт из Contact в ContactsRegister
    
    Args:
        db: Сессия БД
        old_contact: Старый контакт
        dry_run: Если True, только проверяет без сохранения
        
    Returns:
        Результат миграции
    """
    try:
        # Проверяем, не существует ли уже такой контакт
        existing = db.query(ContactsRegister).filter(
            ContactsRegister.user_id == old_contact.user_id,
            ContactsRegister.name == old_contact.name,
            ContactsRegister.birth_date == parse_date(old_contact.birth_date) if old_contact.birth_date else None
        ).first()
        
        if existing:
            return {
                'status': 'skipped',
                'reason': 'already_exists',
                'contact_id': existing.id,
                'old_contact_id': old_contact.id
            }
        
        if dry_run:
            return {
                'status': 'would_create',
                'old_contact_id': old_contact.id,
                'name': old_contact.name
            }
        
        # Парсим дату и время
        birth_date = parse_date(old_contact.birth_date)
        birth_time = parse_time(old_contact.birth_time)
        
        # Преобразуем aliases в теги
        tags = []
        if old_contact.aliases:
            if isinstance(old_contact.aliases, list):
                tags = old_contact.aliases
            else:
                tags = [str(old_contact.aliases)]
        
        # Добавляем custom_title в теги, если есть
        if old_contact.custom_title and old_contact.custom_title not in tags:
            tags.append(old_contact.custom_title)
        
        # Создаем контакт в регистре
        contact = registers_service.create_contact(
            db=db,
            user_id=old_contact.user_id,
            name=old_contact.name,
            relationship_type=old_contact.relationship_type,
            birth_date=birth_date,
            birth_time=birth_time,
            birth_place=old_contact.birth_place,
            tags=tags if tags else None
        )
        
        return {
            'status': 'success',
            'old_contact_id': old_contact.id,
            'new_contact_id': contact.id,
            'name': contact.name
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'old_contact_id': old_contact.id,
            'error': str(e)
        }


def migrate_all_contacts(
    db: Session,
    user_id: Optional[int] = None,
    dry_run: bool = False,
    limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    Мигрирует все контакты из Contact в ContactsRegister
    
    Args:
        db: Сессия БД
        user_id: Если указан, мигрирует только для этого пользователя
        dry_run: Если True, только проверяет без сохранения
        limit: Максимальное количество записей для миграции
        
    Returns:
        Статистика миграции
    """
    # Получаем контакты для миграции
    query = db.query(Contact)
    
    if user_id:
        query = query.filter(Contact.user_id == user_id)
    
    if limit:
        query = query.limit(limit)
    
    contacts = query.all()
    
    print(f"📊 Найдено контактов для миграции: {len(contacts)}")
    
    if dry_run:
        print("🔍 Режим проверки (dry_run=True) - изменения не будут сохранены")
    
    results = {
        'total': len(contacts),
        'success': 0,
        'skipped': 0,
        'errors': 0,
        'details': []
    }
    
    for i, contact in enumerate(contacts, 1):
        if i % 100 == 0:
            print(f"⏳ Обработано: {i}/{len(contacts)}")
        
        result = migrate_contact(db, contact, dry_run=dry_run)
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
    
    parser = argparse.ArgumentParser(description='Миграция данных из Contact в ContactsRegister')
    parser.add_argument('--dry-run', action='store_true', help='Режим проверки без сохранения')
    parser.add_argument('--user-id', type=int, help='Мигрировать только для указанного пользователя')
    parser.add_argument('--limit', type=int, help='Максимальное количество записей')
    
    args = parser.parse_args()
    
    db = SessionLocal()
    try:
        results = migrate_all_contacts(
            db=db,
            user_id=args.user_id,
            dry_run=args.dry_run,
            limit=args.limit
        )
        
        # Выводим статистику
        print("\n📊 Статистика миграции:")
        print(f"   Всего контактов: {results['total']}")
        print(f"   Успешно: {results['success']}")
        print(f"   Пропущено: {results['skipped']}")
        print(f"   Ошибок: {results['errors']}")
        
    except Exception as e:
        print(f"❌ Ошибка при миграции: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()

