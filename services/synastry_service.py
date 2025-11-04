from typing import Dict, List


class SynastryService:
    def __init__(self):
        self.aspects_interpretation = {
            'conjunction': {
                'harmony': 'сильное соединение энергий',
                'challenge': 'возможное слияние или конфликт интересов'
            },
            'sextile': {
                'harmony': 'гармоничное взаимодействие',
                'challenge': 'легкое напряжение'
            },
            'square': {
                'harmony': 'стимул для роста',
                'challenge': 'напряжение и конфликты'
            },
            'trine': {
                'harmony': 'естественная поддержка',
                'challenge': 'возможная пассивность'
            },
            'opposition': {
                'harmony': 'баланс противоположностей',
                'challenge': 'полярность и противостояние'
            }
        }

    def analyze_synastry(self, user_chart: Dict, contact_chart: Dict) -> Dict:
        """Анализ синастрии между двумя картами"""
        aspects = []

        # Анализ основных планет
        for planet in ['sun', 'moon', 'venus', 'mars']:
            if planet in user_chart['planets'] and planet in contact_chart['planets']:
                user_pos = user_chart['planets'][planet]['longitude']
                contact_pos = contact_chart['planets'][planet]['longitude']

                aspect = self._calculate_aspect(user_pos, contact_pos)
                if aspect:
                    aspects.append({
                        'planet': planet,
                        'aspect': aspect['name'],
                        'interpretation': self.aspects_interpretation[aspect['name']]
                    })

        return {
            'aspects': aspects,
            'summary': self._generate_synastry_summary(aspects),
            'compatibility_score': self._calculate_compatibility_score(aspects)
        }

    def _calculate_aspect(self, pos1: float, pos2: float) -> Dict:
        """Расчет аспекта между двумя позициями"""
        diff = abs(pos1 - pos2)
        if diff > 180:
            diff = 360 - diff

        aspects = [
            (0, 8, 'conjunction'),
            (60, 6, 'sextile'),
            (90, 8, 'square'),
            (120, 8, 'trine'),
            (180, 8, 'opposition')
        ]

        for aspect_angle, orb, aspect_name in aspects:
            if abs(diff - aspect_angle) <= orb:
                return {
                    'name': aspect_name,
                    'angle': aspect_angle,
                    'orb': abs(diff - aspect_angle)
                }

        return None

    def _generate_synastry_summary(self, aspects: List[Dict]) -> str:
        """Генерация сводки по синастрии"""
        if not aspects:
            return "Минимальные аспекты взаимодействия"

        harmony_aspects = [a for a in aspects if a['aspect'] in ['sextile', 'trine']]
        challenge_aspects = [a for a in aspects if a['aspect'] in ['square', 'opposition']]

        summary = f"Всего аспектов: {len(aspects)} "
        summary += f"(гармоничные: {len(harmony_aspects)}, напряженные: {len(challenge_aspects)})"

        return summary

    def _calculate_compatibility_score(self, aspects: List[Dict]) -> int:
        """Расчет балла совместимости"""
        if not aspects:
            return 50

        score = 50
        for aspect in aspects:
            if aspect['aspect'] in ['sextile', 'trine']:
                score += 10
            elif aspect['aspect'] in ['square', 'opposition']:
                score -= 5
            elif aspect['aspect'] == 'conjunction':
                score += 5

        return max(0, min(100, score))


synastry_service = SynastryService()