from typing import List, Dict, Optional
from datetime import datetime, timedelta
import re


class ContextService:
    def __init__(self):
        self.keyword_patterns = {
            'work': ['работа', 'карьера', 'проект', 'начальник', 'коллеги', 'задача'],
            'relationships': ['отношения', 'партнер', 'любовь', 'семья', 'друг', 'общение'],
            'health': ['здоровье', 'самочувствие', 'болезнь', 'врач', 'энергия'],
            'finance': ['деньги', 'финансы', 'покупка', 'инвестиции', 'бюджет'],
            'spirituality': ['духовность', 'медитация', 'смысл', 'развитие', 'осознанность']
        }

    def extract_context_from_message(self, message: str, ai_response: str) -> Dict:
        """Извлечение контекста из сообщения и ответа ИИ"""
        context = {
            'event': self._extract_event(message),
            'emotion': self._extract_emotion(message),
            'tags': self._extract_tags(message + " " + ai_response),
            'astro_context': self._extract_astro_context(ai_response)
        }

        # Очищаем пустые поля
        return {k: v for k, v in context.items() if v}

    def _extract_event(self, text: str) -> Optional[str]:
        """Извлечение события из текста"""
        event_indicators = ['сегодня', 'вчера', 'завтра', 'собираюсь', 'планирую', 'произошло']
        sentences = text.split('.')

        for sentence in sentences:
            if any(indicator in sentence.lower() for indicator in event_indicators):
                return sentence.strip()

        return None

    def _extract_emotion(self, text: str) -> Optional[str]:
        """Извлечение эмоций из текста"""
        emotions = {
            'радость': ['рад', 'счастлив', 'восторг', 'удовольствие'],
            'грусть': ['грустно', 'печаль', 'тоска', 'уныние'],
            'злость': ['злой', 'раздражен', 'гнев', 'бесит'],
            'страх': ['боюсь', 'страх', 'тревога', 'опасение'],
            'удивление': ['удивлен', 'неожиданно', 'потрясен']
        }

        text_lower = text.lower()
        for emotion, keywords in emotions.items():
            if any(keyword in text_lower for keyword in keywords):
                return emotion

        return None

    def _extract_tags(self, text: str) -> List[str]:
        """Извлечение тегов из текста"""
        tags = []
        text_lower = text.lower()

        for category, keywords in self.keyword_patterns.items():
            if any(keyword in text_lower for keyword in keywords):
                tags.append(category)

        astro_terms = ['меркурий', 'венера', 'марс', 'юпитер', 'сатурн', 'транзит', 'аспект']
        if any(term in text_lower for term in astro_terms):
            tags.append('астрология')

        return tags

    def _extract_astro_context(self, text: str) -> Optional[str]:
        """Извлечение астрологического контекста из ответа ИИ"""
        astro_pattern = r'(Меркурий|Венера|Марс|Юпитер|Сатурн|Уран|Нептун|Плутон|Луна|Солнце).*?(аспект|транзит|соединение|квадрат|трин)'
        matches = re.findall(astro_pattern, text, re.IGNORECASE)

        if matches:
            return "; ".join([" ".join(match) for match in matches])

        return None

    def get_relevant_context(self,
                             user_id: int,
                             db,
                             current_tags: List[str] = None,
                             limit: int = 5) -> List[Dict]:
        """Получение релевантного контекста для пользователя"""
        from database.models import ContextEntry

        query = db.query(ContextEntry).filter(ContextEntry.user_id == user_id)

        if current_tags:
            relevant_entries = []
            for entry in query.all():
                if entry.tags and any(tag in entry.tags for tag in current_tags):
                    relevant_entries.append(entry)
                if len(relevant_entries) >= limit:
                    break

            return [
                {
                    'id': entry.id,
                    'event': entry.event,
                    'emotion': entry.emotion,
                    'insight': entry.insight,
                    'tags': entry.tags,
                    'created_at': entry.created_at
                }
                for entry in relevant_entries
            ]

        recent_entries = query.order_by(ContextEntry.created_at.desc()).limit(limit).all()

        return [
            {
                'id': entry.id,
                'event': entry.event,
                'emotion': entry.emotion,
                'insight': entry.insight,
                'tags': entry.tags,
                'created_at': entry.created_at
            }
            for entry in recent_entries
        ]


context_service = ContextService()