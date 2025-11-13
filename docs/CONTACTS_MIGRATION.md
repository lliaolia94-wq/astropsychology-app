# Миграция контактов на регистры

## Обзор

Старые endpoints `/contacts` и `/users/{user_id}/contacts` теперь используют `ContactsRegister` вместо старой таблицы `contacts`. Это обеспечивает:

- Единообразное хранение данных в регистрах
- Расширенные возможности (астрологические данные, динамика отношений)
- Обратную совместимость со старыми схемами API

## Что изменилось

### Endpoints

**Старые endpoints остаются доступными, но используют новую таблицу:**

- `POST /contacts` - создает контакт в `contacts_register`
- `GET /users/{user_id}/contacts` - получает контакты из `contacts_register`

**Новые endpoints в регистрах:**

- `POST /api/v1/registers/contacts` - полный функционал регистра
- `GET /api/v1/registers/contacts` - список контактов
- `GET /api/v1/registers/contacts/{contact_id}` - получение контакта
- `PUT /api/v1/registers/contacts/{contact_id}` - обновление контакта
- `DELETE /api/v1/registers/contacts/{contact_id}` - удаление контакта

### Модель данных

**Старая модель `Contact`:**
- `id`, `user_id`, `name`, `relationship_type`
- `custom_title`, `birth_date` (строка), `birth_time` (строка)
- `birth_place`, `aliases` (JSON массив)

**Новая модель `ContactsRegister`:**
- Все поля старой модели
- `birth_date` (Date), `birth_time` (Time) - типизированные поля
- `tags` вместо `aliases` (более универсально)
- Дополнительные поля: `relationship_depth`, `natal_chart_data`, `synastry_with_user`, `composite_chart`, `interaction_frequency`, `last_interaction_date`, `emotional_pattern`, `privacy_level`, `is_active`

## Миграция данных

### Шаг 1: Миграция существующих данных

Если у вас есть данные в старой таблице `contacts`, выполните миграцию:

```bash
# Проверка (dry-run)
python scripts/migrate_contacts_to_register.py --dry-run

# Реальная миграция
python scripts/migrate_contacts_to_register.py

# Миграция для конкретного пользователя
python scripts/migrate_contacts_to_register.py --user-id 123

# Миграция с ограничением
python scripts/migrate_contacts_to_register.py --limit 100
```

### Шаг 2: Проверка миграции

После миграции проверьте:

```python
from app.core.database import SessionLocal
from app.models.database.models import Contact, ContactsRegister

db = SessionLocal()

# Проверяем количество контактов
old_count = db.query(Contact).count()
new_count = db.query(ContactsRegister).count()

print(f"Старых контактов: {old_count}")
print(f"Новых контактов: {new_count}")
```

## Обратная совместимость

### API совместимость

Старые endpoints продолжают работать с теми же схемами:

```python
# Старый способ (все еще работает)
POST /contacts
{
    "name": "Иван Иванов",
    "relationship_type": "друг",
    "birth_date": "1990-05-15",
    "birth_time": "14:30",
    "birth_place": "Москва"
}

# Новый способ (рекомендуется)
POST /api/v1/registers/contacts
{
    "name": "Иван Иванов",
    "relationship_type": "friend",
    "birth_date": "1990-05-15",
    "birth_time": "14:30",
    "birth_place": "Москва",
    "relationship_depth": 8,
    "tags": ["близкий друг"]
}
```

### Преобразование данных

При использовании старых endpoints данные автоматически преобразуются:

- `custom_title` → сохраняется в `tags[0]`
- `aliases` → преобразуются в `tags`
- Строковые даты → преобразуются в Date/Time объекты

## Использование в коде

### Старый способ (deprecated)

```python
from app.models.database.models import Contact

contacts = db.query(Contact).filter(Contact.user_id == user_id).all()
```

### Новый способ (рекомендуется)

```python
from app.models.database.models import ContactsRegister
from app.services.registers_service import registers_service

# Через сервис
contacts = registers_service._get_contacts(query, db)

# Или напрямую
contacts = db.query(ContactsRegister).filter(
    ContactsRegister.user_id == user_id,
    ContactsRegister.is_active == True
).all()
```

## Удаление старой таблицы

⚠️ **ВНИМАНИЕ:** Не удаляйте старую таблицу `contacts` сразу после миграции!

Рекомендуется:

1. Выполнить миграцию данных
2. Проверить работоспособность в течение 1-2 недель
3. Убедиться, что все данные мигрированы
4. Только после этого можно удалить старую таблицу

Для удаления создайте миграцию:

```python
# В новой миграции (009_remove_old_contacts.py)
def upgrade():
    # Удаляем таблицу только если contacts_register не пуста
    op.drop_table('contacts')
```

## Обновленные файлы

- ✅ `app/api/v1/endpoints/contacts.py` - использует ContactsRegister
- ✅ `app/api/v1/endpoints/ai.py` - использует ContactsRegister для поиска контактов
- ✅ `scripts/migrate_contacts_to_register.py` - скрипт миграции данных

## FAQ

**Q: Нужно ли обновлять клиентский код?**
A: Нет, старые endpoints работают с теми же схемами. Но рекомендуется перейти на новые endpoints для доступа к расширенному функционалу.

**Q: Что происходит с данными при миграции?**
A: Данные копируются из `contacts` в `contacts_register`. Старая таблица остается нетронутой.

**Q: Можно ли использовать обе таблицы одновременно?**
A: Технически да, но не рекомендуется. Все новые операции должны использовать `contacts_register`.

**Q: Что делать с дубликатами?**
A: Скрипт миграции автоматически пропускает дубликаты (по user_id, name, birth_date).

