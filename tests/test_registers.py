"""
Тесты для системы регистров контекстной информации
Используются реальные данные из БД, без заглушек
"""
import pytest
from datetime import datetime, date, time, timedelta, timezone
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, Base, engine
from app.models.database.models import (
    User, EventsRegister, ContactsRegister, TransitsRegister,
    VirtualSlices, KarmicThemesRegister, ChatSession
)
from app.services.registers_service import registers_service
from app.services.context_query import ContextQuery, ContextSlice


@pytest.fixture(scope="function")
def db_session():
    """Создает сессию БД для теста"""
    # Создаем все таблицы
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Очищаем таблицы после теста
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_user(db_session: Session):
    """Создает тестового пользователя"""
    user = User(
        phone="+79991234567",
        password_hash="test_hash",
        phone_verified=1,
        name="Тестовый Пользователь",
        birth_date_detailed=date(1990, 5, 15),
        birth_time_detailed=time(14, 30),
        birth_time_utc=datetime(1990, 5, 15, 11, 30, 0, tzinfo=timezone.utc),
        birth_location_name="Москва",
        birth_country="Россия",
        birth_latitude=55.7558,
        birth_longitude=37.6173,
        timezone_name="Europe/Moscow"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_session(db_session: Session, test_user: User):
    """Создает тестовую сессию чата"""
    session = ChatSession(
        user_id=test_user.id,
        title="Тестовая сессия",
        is_active=1,
        session_type="regular"
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    return session


class TestEventsRegister:
    """Тесты для регистра событий"""
    
    def test_create_event(self, db_session: Session, test_user: User, test_session: ChatSession):
        """Тест создания события"""
        event = registers_service.create_event(
            db=db_session,
            user_id=test_user.id,
            event_type='user_message',
            category='career',
            event_date=datetime.now(timezone.utc),
            effective_from=datetime.now(timezone.utc),
            effective_to=None,
            title='Тестовое событие',
            description='Описание события',
            user_message='Сообщение пользователя',
            emotional_state='anxiety',
            emotional_intensity=0.7,
            priority=4,
            tags=['работа', 'конфликт'],
            session_id=test_session.id
        )
        
        assert event.id is not None
        assert event.user_id == test_user.id
        assert event.event_type == 'user_message'
        assert event.category == 'career'
        assert event.title == 'Тестовое событие'
        assert event.emotional_state == 'anxiety'
        assert event.priority == 4
        assert event.tags == ['работа', 'конфликт']
    
    def test_get_event_by_id(self, db_session: Session, test_user: User):
        """Тест получения события по ID"""
        # Создаем событие
        event = registers_service.create_event(
            db=db_session,
            user_id=test_user.id,
            event_type='life_event',
            category='relationships',
            event_date=datetime.now(timezone.utc),
            effective_from=datetime.now(timezone.utc),
            title='Событие для получения'
        )
        
        # Получаем событие
        retrieved = registers_service.get_event_by_id(db_session, event.id)
        
        assert retrieved is not None
        assert retrieved.id == event.id
        assert retrieved.title == 'Событие для получения'
        assert retrieved.category == 'relationships'
    
    def test_update_event(self, db_session: Session, test_user: User):
        """Тест обновления события"""
        # Создаем событие
        event = registers_service.create_event(
            db=db_session,
            user_id=test_user.id,
            event_type='life_event',
            category='health',
            event_date=datetime.now(timezone.utc),
            effective_from=datetime.now(timezone.utc),
            title='Исходное название',
            priority=2
        )
        
        # Обновляем событие
        updated = registers_service.update_event(
            db_session,
            event.id,
            title='Обновленное название',
            priority=5,
            emotional_state='joy'
        )
        
        assert updated is not None
        assert updated.title == 'Обновленное название'
        assert updated.priority == 5
        assert updated.emotional_state == 'joy'
    
    def test_delete_event(self, db_session: Session, test_user: User):
        """Тест удаления события"""
        # Создаем событие
        event = registers_service.create_event(
            db=db_session,
            user_id=test_user.id,
            event_type='life_event',
            category='finance',
            event_date=datetime.now(timezone.utc),
            effective_from=datetime.now(timezone.utc)
        )
        
        event_id = event.id
        
        # Удаляем событие
        success = registers_service.delete_event(db_session, event_id)
        
        assert success is True
        
        # Проверяем, что событие удалено
        deleted = registers_service.get_event_by_id(db_session, event_id)
        assert deleted is None


class TestContactsRegister:
    """Тесты для регистра контактов"""
    
    def test_create_contact(self, db_session: Session, test_user: User):
        """Тест создания контакта"""
        contact = registers_service.create_contact(
            db=db_session,
            user_id=test_user.id,
            name='Иван Иванов',
            relationship_type='colleague',
            relationship_depth=7,
            birth_date=date(1985, 3, 20),
            birth_time=time(12, 0),
            birth_place='Санкт-Петербург',
            tags=['бизнес', 'поддерживающий']
        )
        
        assert contact.id is not None
        assert contact.user_id == test_user.id
        assert contact.name == 'Иван Иванов'
        assert contact.relationship_type == 'colleague'
        assert contact.relationship_depth == 7
        assert contact.birth_date == date(1985, 3, 20)
        assert contact.is_active is True
    
    def test_get_contact_by_id(self, db_session: Session, test_user: User):
        """Тест получения контакта по ID"""
        contact = registers_service.create_contact(
            db=db_session,
            user_id=test_user.id,
            name='Мария Петрова',
            relationship_type='friend'
        )
        
        retrieved = registers_service.get_contact_by_id(db_session, contact.id)
        
        assert retrieved is not None
        assert retrieved.id == contact.id
        assert retrieved.name == 'Мария Петрова'
    
    def test_update_contact(self, db_session: Session, test_user: User):
        """Тест обновления контакта"""
        contact = registers_service.create_contact(
            db=db_session,
            user_id=test_user.id,
            name='Исходное имя',
            relationship_type='friend',
            relationship_depth=5
        )
        
        updated = registers_service.update_contact(
            db_session,
            contact.id,
            name='Обновленное имя',
            relationship_depth=8,
            tags=['обновленный', 'тег']
        )
        
        assert updated is not None
        assert updated.name == 'Обновленное имя'
        assert updated.relationship_depth == 8
        assert updated.tags == ['обновленный', 'тег']
    
    def test_delete_contact_soft(self, db_session: Session, test_user: User):
        """Тест мягкого удаления контакта"""
        contact = registers_service.create_contact(
            db=db_session,
            user_id=test_user.id,
            name='Контакт для удаления',
            relationship_type='colleague'
        )
        
        assert contact.is_active is True
        
        # Мягкое удаление
        success = registers_service.delete_contact(db_session, contact.id)
        
        assert success is True
        
        # Проверяем, что контакт помечен как неактивный
        deleted = registers_service.get_contact_by_id(db_session, contact.id)
        assert deleted is not None
        assert deleted.is_active is False


class TestTransitsRegister:
    """Тесты для регистра транзитов"""
    
    def test_create_transit(self, db_session: Session, test_user: User):
        """Тест создания транзита"""
        transit = registers_service.create_transit(
            db=db_session,
            user_id=test_user.id,
            transit_type='planet_transit',
            planet_from='mars',
            planet_to='sun',
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 15),
            transit_date=date(2025, 1, 8),
            impact_level='high',
            aspect_type='square',
            interpretation='Марс в квадрате к Солнцу',
            impact_areas=['career', 'relationships']
        )
        
        assert transit.id is not None
        assert transit.user_id == test_user.id
        assert transit.transit_type == 'planet_transit'
        assert transit.planet_from == 'mars'
        assert transit.planet_to == 'sun'
        assert transit.impact_level == 'high'
        assert transit.aspect_type == 'square'
        assert transit.impact_areas == ['career', 'relationships']
    
    def test_get_transit_by_id(self, db_session: Session, test_user: User):
        """Тест получения транзита по ID"""
        transit = registers_service.create_transit(
            db=db_session,
            user_id=test_user.id,
            transit_type='planet_transit',
            planet_from='venus',
            start_date=date(2025, 2, 1),
            end_date=date(2025, 2, 10),
            transit_date=date(2025, 2, 5),
            impact_level='medium'
        )
        
        retrieved = registers_service.get_transit_by_id(db_session, transit.id)
        
        assert retrieved is not None
        assert retrieved.id == transit.id
        assert retrieved.planet_from == 'venus'
    
    def test_update_transit(self, db_session: Session, test_user: User):
        """Тест обновления транзита"""
        transit = registers_service.create_transit(
            db=db_session,
            user_id=test_user.id,
            transit_type='planet_transit',
            planet_from='mercury',
            start_date=date(2025, 3, 1),
            end_date=date(2025, 3, 10),
            transit_date=date(2025, 3, 5),
            impact_level='low',
            interpretation='Исходная интерпретация'
        )
        
        updated = registers_service.update_transit(
            db_session,
            transit.id,
            interpretation='Обновленная интерпретация',
            impact_level='critical'
        )
        
        assert updated is not None
        assert updated.interpretation == 'Обновленная интерпретация'
        assert updated.impact_level == 'critical'


class TestContextQuery:
    """Тесты для контекстных запросов"""
    
    def test_query_by_period(self, db_session: Session, test_user: User):
        """Тест запроса по периоду"""
        # Создаем несколько событий
        now = datetime.now(timezone.utc)
        
        event1 = registers_service.create_event(
            db=db_session,
            user_id=test_user.id,
            event_type='user_message',
            category='career',
            event_date=now - timedelta(days=5),
            effective_from=now - timedelta(days=5),
            title='Событие 5 дней назад'
        )
        
        event2 = registers_service.create_event(
            db=db_session,
            user_id=test_user.id,
            event_type='life_event',
            category='relationships',
            event_date=now - timedelta(days=10),
            effective_from=now - timedelta(days=10),
            title='Событие 10 дней назад'
        )
        
        # Запрос за последние 7 дней
        query = ContextQuery(user_id=test_user.id, db=db_session)
        query.for_days(7)
        result = query.execute()
        
        assert len(result.events) >= 1
        # Проверяем, что событие 5 дней назад включено
        event_ids = [e['id'] for e in result.events]
        assert event1.id in event_ids
        # Событие 10 дней назад не должно быть включено
        assert event2.id not in event_ids
    
    def test_query_by_categories(self, db_session: Session, test_user: User):
        """Тест запроса по категориям"""
        now = datetime.now(timezone.utc)
        
        # Создаем события разных категорий
        career_event = registers_service.create_event(
            db=db_session,
            user_id=test_user.id,
            event_type='life_event',
            category='career',
            event_date=now,
            effective_from=now,
            title='Карьерное событие'
        )
        
        health_event = registers_service.create_event(
            db=db_session,
            user_id=test_user.id,
            event_type='life_event',
            category='health',
            event_date=now,
            effective_from=now,
            title='Событие о здоровье'
        )
        
        # Запрос только по категории career
        query = ContextQuery(user_id=test_user.id, db=db_session)
        query.for_days(30).with_categories(['career'])
        result = query.execute()
        
        event_ids = [e['id'] for e in result.events]
        assert career_event.id in event_ids
        assert health_event.id not in event_ids
    
    def test_query_with_emotional_state(self, db_session: Session, test_user: User):
        """Тест запроса по эмоциональному состоянию"""
        now = datetime.now(timezone.utc)
        
        anxiety_event = registers_service.create_event(
            db=db_session,
            user_id=test_user.id,
            event_type='user_message',
            category='relationships',
            event_date=now,
            effective_from=now,
            emotional_state='anxiety',
            emotional_intensity=0.8
        )
        
        joy_event = registers_service.create_event(
            db=db_session,
            user_id=test_user.id,
            event_type='life_event',
            category='career',
            event_date=now,
            effective_from=now,
            emotional_state='joy',
            emotional_intensity=0.9
        )
        
        # Запрос только по anxiety
        query = ContextQuery(user_id=test_user.id, db=db_session)
        query.for_days(30).with_emotional_state(['anxiety'])
        result = query.execute()
        
        event_ids = [e['id'] for e in result.events]
        assert anxiety_event.id in event_ids
        assert joy_event.id not in event_ids
    
    def test_query_with_transits(self, db_session: Session, test_user: User):
        """Тест запроса с транзитами"""
        # Создаем транзит
        transit = registers_service.create_transit(
            db=db_session,
            user_id=test_user.id,
            transit_type='planet_transit',
            planet_from='mars',
            start_date=date.today() - timedelta(days=5),
            end_date=date.today() + timedelta(days=5),
            transit_date=date.today(),
            impact_level='high'
        )
        
        # Запрос с транзитами
        query = ContextQuery(user_id=test_user.id, db=db_session)
        query.for_days(30).include_transits()
        result = query.execute()
        
        assert result.transits is not None
        assert len(result.transits) >= 1
        transit_ids = [t['id'] for t in result.transits]
        assert transit.id in transit_ids
    
    def test_query_statistics(self, db_session: Session, test_user: User):
        """Тест вычисления статистики"""
        now = datetime.now(timezone.utc)
        
        # Создаем события разных категорий
        for i, category in enumerate(['career', 'health', 'career', 'relationships']):
            registers_service.create_event(
                db=db_session,
                user_id=test_user.id,
                event_type='life_event',
                category=category,
                event_date=now - timedelta(days=i),
                effective_from=now - timedelta(days=i),
                priority=3 + (i % 2)
            )
        
        query = ContextQuery(user_id=test_user.id, db=db_session)
        query.for_days(30)
        result = query.execute()
        
        assert 'statistics' in result.statistics
        assert result.statistics['events_count'] >= 4
        assert 'career' in result.statistics['categories']
        assert result.statistics['categories']['career'] == 2
    
    def test_query_patterns(self, db_session: Session, test_user: User):
        """Тест выявления паттернов"""
        now = datetime.now(timezone.utc)
        
        # Создаем несколько событий с одинаковым эмоциональным состоянием
        for i in range(5):
            registers_service.create_event(
                db=db_session,
                user_id=test_user.id,
                event_type='user_message',
                category='career',
                event_date=now - timedelta(days=i),
                effective_from=now - timedelta(days=i),
                emotional_state='anxiety'
            )
        
        query = ContextQuery(user_id=test_user.id, db=db_session)
        query.for_days(30)
        result = query.execute()
        
        assert len(result.patterns) > 0
        # Проверяем наличие паттерна эмоционального повторения
        pattern_types = [p['type'] for p in result.patterns]
        assert 'emotional_repetition' in pattern_types


class TestIntegration:
    """Интеграционные тесты"""
    
    def test_full_workflow(self, db_session: Session, test_user: User, test_session: ChatSession):
        """Полный рабочий процесс: создание событий, контактов, транзитов и запрос"""
        now = datetime.now(timezone.utc)
        
        # 1. Создаем контакт
        contact = registers_service.create_contact(
            db=db_session,
            user_id=test_user.id,
            name='Тестовый Контакт',
            relationship_type='friend',
            relationship_depth=8
        )
        
        # 2. Создаем транзит
        transit = registers_service.create_transit(
            db=db_session,
            user_id=test_user.id,
            transit_type='planet_transit',
            planet_from='venus',
            start_date=date.today() - timedelta(days=2),
            end_date=date.today() + timedelta(days=2),
            transit_date=date.today(),
            impact_level='medium'
        )
        
        # 3. Создаем событие с ссылкой на контакт
        event = registers_service.create_event(
            db=db_session,
            user_id=test_user.id,
            event_type='life_event',
            category='relationships',
            event_date=now,
            effective_from=now,
            title='Встреча с другом',
            description='Встретился с тестовым контактом',
            contact_ids=[contact.id],
            emotional_state='joy',
            priority=4,
            session_id=test_session.id
        )
        
        # 4. Выполняем комплексный запрос
        query = ContextQuery(user_id=test_user.id, db=db_session)
        query.for_days(7).include_contacts().include_transits().with_categories(['relationships'])
        result = query.execute()
        
        # Проверяем результаты
        assert len(result.events) >= 1
        assert result.contacts is not None
        assert len(result.contacts) >= 1
        assert result.transits is not None
        assert len(result.transits) >= 1
        
        # Проверяем связи
        event_dict = next(e for e in result.events if e['id'] == event.id)
        assert contact.id in event_dict['contact_ids']
        
        # Проверяем статистику
        assert result.statistics['events_count'] >= 1
        assert result.statistics['contacts_count'] >= 1
        assert result.statistics['transits_count'] >= 1

