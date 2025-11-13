"""
Сервис для работы с регистрами контекстной информации
"""
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc

from app.models.database.models import (
    EventsRegister, ContactsRegister, TransitsRegister,
    VirtualSlices, KarmicThemesRegister, User
)
from app.services.context_query import ContextQuery, ContextSlice
from app.services.astro_service import astro_service
from app.services.natal_chart_service import natal_chart_service

logger = logging.getLogger(__name__)


class RegistersService:
    """Сервис для работы с регистрами контекстной информации"""
    
    def execute_query(self, query: ContextQuery, db: Session) -> ContextSlice:
        """
        Выполняет параметризованный запрос и возвращает виртуальный срез
        
        Args:
            query: Объект ContextQuery с параметрами запроса
            db: Сессия базы данных
            
        Returns:
            ContextSlice с результатами
        """
        slice_result = ContextSlice()
        
        # Получаем события
        events = self._get_events(query, db)
        slice_result.events = events
        
        # Получаем контакты, если запрошены
        if query.include_contacts:
            contacts = self._get_contacts(query, db)
            slice_result.contacts = contacts
        
        # Получаем транзиты, если запрошены
        if query.include_transits:
            transits = self._get_transits(query, db)
            slice_result.transits = transits
        
        # Вычисляем статистику
        slice_result.statistics = self._calculate_statistics(events, contacts if query.include_contacts else [], 
                                                             transits if query.include_transits else [])
        
        # Выявляем паттерны
        slice_result.patterns = self._detect_patterns(events)
        
        return slice_result
    
    def _get_events(self, query: ContextQuery, db: Session) -> List[Dict[str, Any]]:
        """
        Получение событий по запросу
        
        Args:
            query: Объект ContextQuery
            db: Сессия БД
            
        Returns:
            Список событий в виде словарей
        """
        q = db.query(EventsRegister).filter(EventsRegister.user_id == query.user_id)
        
        # Фильтр по времени
        if query.time_range:
            start = query.time_range.get('start')
            end = query.time_range.get('end')
            if start:
                q = q.filter(EventsRegister.event_date >= start)
            if end:
                q = q.filter(EventsRegister.event_date <= end)
        
        # Фильтр по категориям
        if query.categories:
            q = q.filter(EventsRegister.category.in_(query.categories))
        
        # Фильтр по эмоциональным состояниям
        if query.emotional_states:
            q = q.filter(EventsRegister.emotional_state.in_(query.emotional_states))
        
        # Фильтр по тегам
        if query.tags:
            # Для JSON поля нужно использовать специальные функции
            # В SQLite и PostgreSQL это работает по-разному
            conditions = []
            for tag in query.tags:
                if db.bind.dialect.name == 'postgresql':
                    conditions.append(EventsRegister.tags.contains([tag]))
                else:
                    # SQLite - простой поиск в JSON строке
                    conditions.append(EventsRegister.tags.like(f'%{tag}%'))
            if conditions:
                q = q.filter(or_(*conditions))
        
        # Фильтр по приоритету
        if query.priority_min is not None:
            q = q.filter(EventsRegister.priority >= query.priority_min)
        if query.priority_max is not None:
            q = q.filter(EventsRegister.priority <= query.priority_max)
        
        # Фильтр по актуальности
        now = datetime.now(timezone.utc)
        q = q.filter(
            and_(
                EventsRegister.effective_from <= now,
                or_(
                    EventsRegister.effective_to.is_(None),
                    EventsRegister.effective_to >= now
                )
            )
        )
        
        # Сортировка
        q = q.order_by(desc(EventsRegister.event_date))
        
        # Лимит
        if query.limit:
            q = q.limit(query.limit)
        
        events = q.all()
        
        # Преобразуем в словари
        return [self._event_to_dict(event) for event in events]
    
    def _get_contacts(self, query: ContextQuery, db: Session) -> List[Dict[str, Any]]:
        """
        Получение контактов по запросу
        
        Args:
            query: Объект ContextQuery
            db: Сессия БД
            
        Returns:
            Список контактов в виде словарей
        """
        q = db.query(ContactsRegister).filter(
            and_(
                ContactsRegister.user_id == query.user_id,
                ContactsRegister.is_active == True
            )
        )
        
        # Фильтр по типу отношений
        if query.filters.get('relationship_types'):
            q = q.filter(ContactsRegister.relationship_type.in_(query.filters['relationship_types']))
        
        # Сортировка
        q = q.order_by(desc(ContactsRegister.last_interaction_date))
        
        contacts = q.all()
        
        return [self._contact_to_dict(contact) for contact in contacts]
    
    def _get_transits(self, query: ContextQuery, db: Session) -> List[Dict[str, Any]]:
        """
        Получение транзитов по запросу
        
        Args:
            query: Объект ContextQuery
            db: Сессия БД
            
        Returns:
            Список транзитов в виде словарей
        """
        q = db.query(TransitsRegister).filter(TransitsRegister.user_id == query.user_id)
        
        # Фильтр по времени
        if query.time_range:
            start = query.time_range.get('start')
            end = query.time_range.get('end')
            if start:
                q = q.filter(TransitsRegister.transit_date >= start.date())
            if end:
                q = q.filter(TransitsRegister.transit_date <= end.date())
        
        # Фильтр по уровню влияния
        if query.filters.get('impact_levels'):
            q = q.filter(TransitsRegister.impact_level.in_(query.filters['impact_levels']))
        
        # Фильтр по актуальности
        now = datetime.now().date()
        q = q.filter(
            and_(
                TransitsRegister.start_date <= now,
                TransitsRegister.end_date >= now
            )
        )
        
        # Сортировка
        q = q.order_by(TransitsRegister.transit_date)
        
        transits = q.all()
        
        return [self._transit_to_dict(transit) for transit in transits]
    
    def _event_to_dict(self, event: EventsRegister) -> Dict[str, Any]:
        """Преобразование события в словарь"""
        return {
            'id': event.id,
            'user_id': event.user_id,
            'session_id': event.session_id,
            'event_date': event.event_date.isoformat() if event.event_date else None,
            'created_at': event.created_at.isoformat() if event.created_at else None,
            'effective_from': event.effective_from.isoformat() if event.effective_from else None,
            'effective_to': event.effective_to.isoformat() if event.effective_to else None,
            'event_type': event.event_type,
            'category': event.category,
            'priority': event.priority,
            'title': event.title,
            'description': event.description,
            'user_message': event.user_message,
            'ai_response': event.ai_response,
            'insight_text': event.insight_text,
            'emotional_state': event.emotional_state,
            'emotional_intensity': float(event.emotional_intensity) if event.emotional_intensity else None,
            'emotional_trigger': event.emotional_trigger,
            'astrological_context': event.astrological_context,
            'tags': event.tags,
            'source': event.source,
            'confidence_score': float(event.confidence_score) if event.confidence_score else None,
            'contact_ids': event.contact_ids
        }
    
    def _contact_to_dict(self, contact: ContactsRegister) -> Dict[str, Any]:
        """Преобразование контакта в словарь"""
        return {
            'id': contact.id,
            'user_id': contact.user_id,
            'name': contact.name,
            'relationship_type': contact.relationship_type,
            'relationship_depth': contact.relationship_depth,
            'birth_date': contact.birth_date.isoformat() if contact.birth_date else None,
            'birth_time': contact.birth_time.isoformat() if contact.birth_time else None,
            'birth_place': contact.birth_place,
            'timezone': contact.timezone,
            'natal_chart_data': contact.natal_chart_data,
            'synastry_with_user': contact.synastry_with_user,
            'composite_chart': contact.composite_chart,
            'interaction_frequency': contact.interaction_frequency,
            'last_interaction_date': contact.last_interaction_date.isoformat() if contact.last_interaction_date else None,
            'emotional_pattern': contact.emotional_pattern,
            'tags': contact.tags,
            'is_active': contact.is_active,
            'privacy_level': contact.privacy_level
        }
    
    def _transit_to_dict(self, transit: TransitsRegister) -> Dict[str, Any]:
        """Преобразование транзита в словарь"""
        return {
            'id': transit.id,
            'user_id': transit.user_id,
            'calculation_date': transit.calculation_date.isoformat() if transit.calculation_date else None,
            'start_date': transit.start_date.isoformat() if transit.start_date else None,
            'end_date': transit.end_date.isoformat() if transit.end_date else None,
            'transit_date': transit.transit_date.isoformat() if transit.transit_date else None,
            'transit_type': transit.transit_type,
            'planet_from': transit.planet_from,
            'planet_to': transit.planet_to,
            'aspect_type': transit.aspect_type,
            'exact_time': transit.exact_time.isoformat() if transit.exact_time else None,
            'orb': float(transit.orb) if transit.orb else None,
            'strength': float(transit.strength) if transit.strength else None,
            'house': transit.house,
            'interpretation': transit.interpretation,
            'impact_level': transit.impact_level,
            'impact_areas': transit.impact_areas,
            'related_transit_ids': transit.related_transit_ids,
            'triggered_event_ids': transit.triggered_event_ids
        }
    
    def _calculate_statistics(
        self, 
        events: List[Dict[str, Any]], 
        contacts: List[Dict[str, Any]], 
        transits: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Вычисление статистики по срезу
        
        Args:
            events: Список событий
            contacts: Список контактов
            transits: Список транзитов
            
        Returns:
            Словарь со статистикой
        """
        stats = {
            'events_count': len(events),
            'contacts_count': len(contacts),
            'transits_count': len(transits),
            'categories': {},
            'emotional_states': {},
            'priority_distribution': {},
            'date_range': {}
        }
        
        # Статистика по категориям
        for event in events:
            category = event.get('category')
            if category:
                stats['categories'][category] = stats['categories'].get(category, 0) + 1
        
        # Статистика по эмоциональным состояниям
        for event in events:
            emotional_state = event.get('emotional_state')
            if emotional_state:
                stats['emotional_states'][emotional_state] = stats['emotional_states'].get(emotional_state, 0) + 1
        
        # Распределение по приоритетам
        for event in events:
            priority = event.get('priority', 3)
            stats['priority_distribution'][priority] = stats['priority_distribution'].get(priority, 0) + 1
        
        # Временной диапазон
        if events:
            dates = [datetime.fromisoformat(e['event_date']) for e in events if e.get('event_date')]
            if dates:
                stats['date_range'] = {
                    'start': min(dates).isoformat(),
                    'end': max(dates).isoformat()
                }
        
        return stats
    
    def _detect_patterns(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Выявление паттернов в событиях
        
        Args:
            events: Список событий
            
        Returns:
            Список выявленных паттернов
        """
        patterns = []
        
        # Паттерн: повторяющиеся эмоциональные состояния
        emotional_counts = {}
        for event in events:
            state = event.get('emotional_state')
            if state:
                emotional_counts[state] = emotional_counts.get(state, 0) + 1
        
        for state, count in emotional_counts.items():
            if count >= 3:  # Порог для паттерна
                patterns.append({
                    'type': 'emotional_repetition',
                    'description': f'Повторяющееся эмоциональное состояние: {state}',
                    'frequency': count,
                    'data': {'emotional_state': state}
                })
        
        # Паттерн: повторяющиеся категории
        category_counts = {}
        for event in events:
            category = event.get('category')
            if category:
                category_counts[category] = category_counts.get(category, 0) + 1
        
        for category, count in category_counts.items():
            if count >= 3:
                patterns.append({
                    'type': 'category_repetition',
                    'description': f'Повторяющаяся категория: {category}',
                    'frequency': count,
                    'data': {'category': category}
                })
        
        return patterns
    
    # ============ CRUD операции для EventsRegister ============
    
    def create_event(
        self,
        db: Session,
        user_id: int,
        event_type: str,
        category: str,
        event_date: datetime,
        effective_from: datetime,
        effective_to: Optional[datetime] = None,
        **kwargs
    ) -> EventsRegister:
        """
        Создание нового события
        
        Args:
            db: Сессия БД
            user_id: ID пользователя
            event_type: Тип события
            category: Категория
            event_date: Дата события
            effective_from: Начало периода актуальности
            effective_to: Конец периода актуальности (None = бессрочно)
            **kwargs: Дополнительные поля события
            
        Returns:
            Созданное событие
        """
        event = EventsRegister(
            user_id=user_id,
            event_type=event_type,
            category=category,
            event_date=event_date,
            effective_from=effective_from,
            effective_to=effective_to,
            **kwargs
        )
        
        db.add(event)
        db.commit()
        db.refresh(event)
        
        return event
    
    def get_event_by_id(self, db: Session, event_id: int) -> Optional[EventsRegister]:
        """Получение события по ID"""
        return db.query(EventsRegister).filter(EventsRegister.id == event_id).first()
    
    def update_event(self, db: Session, event_id: int, **kwargs) -> Optional[EventsRegister]:
        """Обновление события"""
        event = self.get_event_by_id(db, event_id)
        if not event:
            return None
        
        for key, value in kwargs.items():
            if hasattr(event, key):
                setattr(event, key, value)
        
        db.commit()
        db.refresh(event)
        
        return event
    
    def delete_event(self, db: Session, event_id: int) -> bool:
        """Удаление события"""
        event = self.get_event_by_id(db, event_id)
        if not event:
            return False
        
        db.delete(event)
        db.commit()
        
        return True
    
    # ============ CRUD операции для ContactsRegister ============
    
    def create_contact(
        self,
        db: Session,
        user_id: int,
        name: str,
        relationship_type: str,
        **kwargs
    ) -> ContactsRegister:
        """
        Создание нового контакта
        
        Args:
            db: Сессия БД
            user_id: ID пользователя
            name: Имя контакта
            relationship_type: Тип отношений
            **kwargs: Дополнительные поля контакта
            
        Returns:
            Созданный контакт
        """
        contact = ContactsRegister(
            user_id=user_id,
            name=name,
            relationship_type=relationship_type,
            **kwargs
        )
        
        db.add(contact)
        db.commit()
        db.refresh(contact)
        
        return contact
    
    def get_contact_by_id(self, db: Session, contact_id: int) -> Optional[ContactsRegister]:
        """Получение контакта по ID"""
        return db.query(ContactsRegister).filter(ContactsRegister.id == contact_id).first()
    
    def update_contact(self, db: Session, contact_id: int, **kwargs) -> Optional[ContactsRegister]:
        """Обновление контакта"""
        contact = self.get_contact_by_id(db, contact_id)
        if not contact:
            return None
        
        for key, value in kwargs.items():
            if hasattr(contact, key):
                setattr(contact, key, value)
        
        contact.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(contact)
        
        return contact
    
    def delete_contact(self, db: Session, contact_id: int) -> bool:
        """Удаление контакта (мягкое удаление - is_active = False)"""
        contact = self.get_contact_by_id(db, contact_id)
        if not contact:
            return False
        
        contact.is_active = False
        contact.updated_at = datetime.now(timezone.utc)
        db.commit()
        
        return True
    
    # ============ CRUD операции для TransitsRegister ============
    
    def create_transit(
        self,
        db: Session,
        user_id: int,
        transit_type: str,
        planet_from: str,
        start_date: datetime.date,
        end_date: datetime.date,
        transit_date: datetime.date,
        impact_level: str,
        **kwargs
    ) -> TransitsRegister:
        """
        Создание нового транзита
        
        Args:
            db: Сессия БД
            user_id: ID пользователя
            transit_type: Тип транзита
            planet_from: Транзитирующая планета
            start_date: Начало периода
            end_date: Конец периода
            transit_date: Конкретная дата транзита
            impact_level: Уровень влияния
            **kwargs: Дополнительные поля транзита
            
        Returns:
            Созданный транзит
        """
        transit = TransitsRegister(
            user_id=user_id,
            transit_type=transit_type,
            planet_from=planet_from,
            calculation_date=datetime.now().date(),
            start_date=start_date,
            end_date=end_date,
            transit_date=transit_date,
            impact_level=impact_level,
            **kwargs
        )
        
        db.add(transit)
        db.commit()
        db.refresh(transit)
        
        return transit
    
    def get_transit_by_id(self, db: Session, transit_id: int) -> Optional[TransitsRegister]:
        """Получение транзита по ID"""
        return db.query(TransitsRegister).filter(TransitsRegister.id == transit_id).first()
    
    def update_transit(self, db: Session, transit_id: int, **kwargs) -> Optional[TransitsRegister]:
        """Обновление транзита"""
        transit = self.get_transit_by_id(db, transit_id)
        if not transit:
            return None
        
        for key, value in kwargs.items():
            if hasattr(transit, key):
                setattr(transit, key, value)
        
        db.commit()
        db.refresh(transit)
        
        return transit
    
    def delete_transit(self, db: Session, transit_id: int) -> bool:
        """Удаление транзита"""
        transit = self.get_transit_by_id(db, transit_id)
        if not transit:
            return False
        
        db.delete(transit)
        db.commit()
        
        return True
    
    def calculate_and_save_transits_for_date(
        self,
        db: Session,
        user: User,
        target_date: datetime.date,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        timezone_name: Optional[str] = None
    ) -> List[TransitsRegister]:
        """
        Рассчитывает и сохраняет транзиты на конкретную дату
        
        Args:
            db: Сессия БД
            user: Пользователь
            target_date: Дата для расчета
            latitude: Широта (если не указана, берется из профиля)
            longitude: Долгота (если не указана, берется из профиля)
            timezone_name: Временная зона (если не указана, берется из профиля)
            
        Returns:
            Список созданных транзитов
        """
        # Получаем натальную карту
        chart_data = natal_chart_service.get_chart_for_user(user, db)
        if not chart_data:
            raise ValueError("Натальная карта не найдена. Сначала рассчитайте карту.")
        
        # Определяем координаты
        if latitude is None or longitude is None:
            if (user.current_latitude is not None and 
                user.current_longitude is not None and
                float(user.current_latitude) != 0 and 
                float(user.current_longitude) != 0):
                latitude = float(user.current_latitude)
                longitude = float(user.current_longitude)
                if timezone_name is None:
                    timezone_name = user.current_timezone_name
            elif (user.birth_latitude is not None and 
                  user.birth_longitude is not None):
                latitude = float(user.birth_latitude)
                longitude = float(user.birth_longitude)
                if timezone_name is None:
                    timezone_name = user.timezone_name
            else:
                raise ValueError("Не указаны координаты для расчета транзитов")
        
        # Конвертируем данные карты
        natal_chart = {
            'planets': chart_data['planets'],
            'houses': chart_data['houses'],
            'angles': chart_data['angles'],
            'aspects': chart_data.get('aspects', [])
        }
        
        # Рассчитываем транзиты
        date_str = target_date.strftime("%Y-%m-%d")
        transits_result = astro_service.calculate_transits(
            natal_chart,
            date_str,
            latitude=latitude,
            longitude=longitude,
            timezone_name=timezone_name
        )
        
        if not transits_result['success']:
            raise ValueError(f"Ошибка расчета транзитов: {transits_result.get('error')}")
        
        # Сохраняем транзиты в регистр
        saved_transits = []
        transits_data = transits_result.get('transits', {})
        
        for planet_key, transit_info in transits_data.items():
            aspect = transit_info.get('aspect')
            if not aspect:
                continue  # Сохраняем только транзиты с аспектами
            
            # Определяем период действия транзита
            transit_start_time = transit_info.get('transit_start_time')
            transit_end_time = transit_info.get('transit_end_time')
            exact_time = transit_info.get('exact_aspect_time')
            
            # Вычисляем период действия (примерно ±3 дня от точного времени)
            exact_dt = None
            if exact_time:
                try:
                    # Пробуем разные форматы времени
                    if isinstance(exact_time, str):
                        if 'Z' in exact_time:
                            exact_dt = datetime.fromisoformat(exact_time.replace('Z', '+00:00'))
                        elif '+' in exact_time or '-' in exact_time[-6:]:
                            exact_dt = datetime.fromisoformat(exact_time)
                        else:
                            # Просто дата и время без timezone
                            exact_dt = datetime.fromisoformat(exact_time)
                    else:
                        exact_dt = exact_time
                    
                    if exact_dt:
                        start_date = (exact_dt - timedelta(days=3)).date()
                        end_date = (exact_dt + timedelta(days=3)).date()
                    else:
                        start_date = target_date
                        end_date = target_date
                except (ValueError, AttributeError) as e:
                    logger.warning(f"Не удалось распарсить exact_time: {exact_time}, ошибка: {e}")
                    start_date = target_date
                    end_date = target_date
            else:
                start_date = target_date
                end_date = target_date
            
            # Определяем уровень влияния по типу аспекта
            aspect_type = aspect.get('name', 'conjunction')
            impact_level = 'medium'
            if aspect_type in ['square', 'opposition']:
                impact_level = 'high'
            elif aspect_type in ['trine', 'sextile']:
                impact_level = 'low'
            
            # Определяем области влияния по планете
            impact_areas = []
            if planet_key in ['sun', 'mars']:
                impact_areas.append('career')
            if planet_key in ['venus', 'moon']:
                impact_areas.append('relationships')
            if planet_key in ['mercury']:
                impact_areas.append('finance')
            if planet_key in ['jupiter', 'saturn']:
                impact_areas.append('spiritual')
            
            # Проверяем, не существует ли уже такой транзит
            existing = db.query(TransitsRegister).filter(
                TransitsRegister.user_id == user.id,
                TransitsRegister.planet_from == planet_key,
                TransitsRegister.transit_date == target_date,
                TransitsRegister.aspect_type == aspect_type
            ).first()
            
            if existing:
                saved_transits.append(existing)
                continue
            
            # Создаем транзит
            transit = self.create_transit(
                db=db,
                user_id=user.id,
                transit_type='planet_transit',
                planet_from=planet_key,
                planet_to=planet_key,  # Транзит к натальной позиции той же планеты
                start_date=start_date,
                end_date=end_date,
                transit_date=target_date,
                impact_level=impact_level,
                aspect_type=aspect_type,
                exact_time=exact_dt if exact_dt else None,
                orb=aspect.get('orb'),
                strength=aspect.get('strength', 1.0 - abs(aspect.get('orb', 0)) / 8.0),
                interpretation=f"{planet_key.capitalize()} в {aspect_type} к натальной позиции",
                impact_areas=impact_areas if impact_areas else None
            )
            
            saved_transits.append(transit)
        
        return saved_transits
    
    def get_or_calculate_transits_for_date(
        self,
        db: Session,
        user: User,
        target_date: datetime.date,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        timezone_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Получает транзиты из регистра или рассчитывает их, если отсутствуют
        
        Args:
            db: Сессия БД
            user: Пользователь
            target_date: Дата для получения транзитов
            latitude: Широта
            longitude: Долгота
            timezone_name: Временная зона
            
        Returns:
            Словарь с транзитами в формате, совместимом со старым API
        """
        # Проверяем, есть ли транзиты в регистре
        transits_in_db = db.query(TransitsRegister).filter(
            TransitsRegister.user_id == user.id,
            TransitsRegister.transit_date == target_date
        ).all()
        
        # Если транзитов нет, рассчитываем и сохраняем
        if not transits_in_db:
            try:
                transits_in_db = self.calculate_and_save_transits_for_date(
                    db=db,
                    user=user,
                    target_date=target_date,
                    latitude=latitude,
                    longitude=longitude,
                    timezone_name=timezone_name
                )
            except Exception as e:
                logger.error(f"Ошибка расчета транзитов: {str(e)}")
                raise ValueError(f"Не удалось рассчитать транзиты: {str(e)}")
        
        # Преобразуем в формат старого API
        transits_dict = {}
        summary_text = ''
        
        for transit in transits_in_db:
            planet_key = transit.planet_from
            transits_dict[planet_key] = {
                'transit_longitude': None,  # Будет заполнено из расчета
                'transit_sign': None,  # Будет заполнено из расчета
                'aspect': {
                    'type': transit.aspect_type,
                    'name': transit.aspect_type,
                    'angle': None,
                    'orb': float(transit.orb) if transit.orb else None
                },
                'is_retrograde': False,  # Будет заполнено из расчета
                'transit_start_time': transit.start_date.isoformat() if transit.start_date else None,
                'transit_end_time': transit.end_date.isoformat() if transit.end_date else None,
                'exact_aspect_time': transit.exact_time.isoformat() if transit.exact_time else None
            }
        
        # Получаем натальную карту для расчета позиций
        chart_data = natal_chart_service.get_chart_for_user(user, db)
        transits_result = None
        
        if chart_data:
            # Рассчитываем транзитные позиции для полной информации
            date_str = target_date.strftime("%Y-%m-%d")
            natal_chart = {
                'planets': chart_data['planets'],
                'houses': chart_data['houses'],
                'angles': chart_data['angles'],
                'aspects': chart_data.get('aspects', [])
            }
            
            # Определяем координаты для расчета
            calc_latitude = latitude
            calc_longitude = longitude
            calc_timezone = timezone_name
            
            if calc_latitude is None or calc_longitude is None:
                if (user.current_latitude is not None and 
                    user.current_longitude is not None and
                    float(user.current_latitude) != 0 and 
                    float(user.current_longitude) != 0):
                    calc_latitude = float(user.current_latitude)
                    calc_longitude = float(user.current_longitude)
                    if calc_timezone is None:
                        calc_timezone = user.current_timezone_name
                elif (user.birth_latitude is not None and 
                      user.birth_longitude is not None):
                    calc_latitude = float(user.birth_latitude)
                    calc_longitude = float(user.birth_longitude)
                    if calc_timezone is None:
                        calc_timezone = user.timezone_name
            
            if calc_latitude and calc_longitude:
                transits_result = astro_service.calculate_transits(
                    natal_chart,
                    date_str,
                    latitude=calc_latitude,
                    longitude=calc_longitude,
                    timezone_name=calc_timezone
                )
                
                if transits_result and transits_result.get('success'):
                    # Объединяем данные из регистра с расчетными позициями
                    calculated_transits = transits_result.get('transits', {})
                    for planet_key, transit_info in calculated_transits.items():
                        if planet_key in transits_dict:
                            transits_dict[planet_key].update({
                                'transit_longitude': transit_info.get('transit_longitude'),
                                'transit_sign': transit_info.get('transit_sign'),
                                'is_retrograde': transit_info.get('is_retrograde', False)
                            })
                    
                    summary_text = transits_result.get('summary', '')
        
        # Если summary не получен, генерируем простой
        if not summary_text:
            aspects_found = []
            for planet_key, transit_info in transits_dict.items():
                aspect = transit_info.get('aspect', {})
                if aspect.get('name'):
                    aspects_found.append(f"{planet_key} {aspect['name']}")
            if aspects_found:
                summary_text = f"Аспекты: {', '.join(aspects_found)}"
            else:
                summary_text = "Нейтральный день. Хорошее время для рутины и планирования."
        
        return {
            'success': True,
            'date': target_date.strftime("%Y-%m-%d"),
            'transits': transits_dict,
            'summary': summary_text
        }
    
    def get_or_calculate_calendar(
        self,
        db: Session,
        user: User,
        year: int,
        month: int
    ) -> Dict[str, Any]:
        """
        Получает календарь транзитов на месяц из регистра или рассчитывает
        
        Args:
            db: Сессия БД
            user: Пользователь
            year: Год
            month: Месяц
            
        Returns:
            Календарь в формате старого API
        """
        from calendar import monthrange
        
        days = []
        _, last_day = monthrange(year, month)
        
        for day in range(1, last_day + 1):
            try:
                target_date = datetime(year, month, day).date()
                
                # Получаем транзиты для дня
                transits_data = self.get_or_calculate_transits_for_date(
                    db=db,
                    user=user,
                    target_date=target_date
                )
                
                if transits_data['success']:
                    transits = transits_data.get('transits', {})
                    
                    # Определяем цвет дня
                    day_color = 'green'
                    hard_aspects = ['square', 'opposition']
                    hard_count = 0
                    
                    for planet_data in transits.values():
                        aspect = planet_data.get('aspect', {})
                        if aspect.get('name') in hard_aspects:
                            hard_count += 1
                    
                    if hard_count >= 2:
                        day_color = 'red'
                    elif hard_count == 1:
                        day_color = 'blue'
                    
                    days.append({
                        'date': target_date.strftime("%Y-%m-%d"),
                        'color': day_color,
                        'description': transits_data.get('summary', ''),
                        'transits': transits
                    })
                    
            except Exception as e:
                logger.error(f"Ошибка обработки дня {day}: {str(e)}")
                continue
        
        return {
            'month': f"{year}-{month:02d}",
            'year': year,
            'days': days
        }


# Глобальный экземпляр сервиса
registers_service = RegistersService()

