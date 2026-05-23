"""
Mystery Service: generates Tuesday challenge events and Saturday answer events
using OpenAI for a given month.
"""
import calendar
import datetime
from django.conf import settings
from django.utils import timezone

from .models import CalendarEvent


class MysteryService:
    def __init__(self, user):
        self.user = user

    def _get_tuesdays(self, year, month):
        cal = calendar.monthcalendar(year, month)
        tuesdays = []
        for week in cal:
            if week[calendar.TUESDAY] != 0:
                tuesdays.append(datetime.date(year, month, week[calendar.TUESDAY]))
        return tuesdays

    def _get_saturdays(self, year, month):
        cal = calendar.monthcalendar(year, month)
        saturdays = []
        for week in cal:
            if week[calendar.SATURDAY] != 0:
                saturdays.append(datetime.date(year, month, week[calendar.SATURDAY]))
        return saturdays

    def _generate_challenge(self, index):
        """Generate a mystery challenge using OpenAI or a fallback."""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{
                    "role": "user",
                    "content": (
                        f"Cria um desafio mistério criativo e divertido número {index} "
                        "para colaboradores de restaurante. "
                        "Formato: Título curto (máx 60 chars) + descrição do desafio (máx 200 chars). "
                        "Responde em JSON: {\"title\": \"...\", \"description\": \"...\", \"answer\": \"...\"}"
                    )
                }],
                response_format={"type": "json_object"},
                max_tokens=300,
            )
            import json
            return json.loads(response.choices[0].message.content)
        except Exception:
            return {
                "title": f"Desafio Mistério #{index}",
                "description": "Um desafio especial para esta semana. Boa sorte!",
                "answer": "A ser revelado no sábado.",
            }

    def generate_for_month(self, restaurant_id, month, year):
        from apps.restaurants.models import Restaurant
        try:
            restaurant = Restaurant.objects.get(id=restaurant_id)
        except Restaurant.DoesNotExist:
            return {'error': 'Restaurante não encontrado.'}

        tuesdays = self._get_tuesdays(year, month)
        saturdays = self._get_saturdays(year, month)

        created_challenges = []
        created_answers = []

        pairs = list(zip(tuesdays, saturdays))

        for i, (tuesday, saturday) in enumerate(pairs, start=1):
            challenge = self._generate_challenge(i)

            # Create Tuesday challenge event
            t_event = CalendarEvent.objects.create(
                title=challenge['title'],
                description=challenge['description'],
                start_date=timezone.make_aware(datetime.datetime.combine(tuesday, datetime.time(9, 0))),
                end_date=timezone.make_aware(datetime.datetime.combine(tuesday, datetime.time(18, 0))),
                event_type='mystery_challenge',
                restaurant=restaurant,
                created_by=self.user,
                color='#8B5CF6',
                event_metadata={'challenge_index': i, 'answer': challenge.get('answer', '')},
            )
            created_challenges.append(t_event.id)

            # Create Saturday answer event
            s_event = CalendarEvent.objects.create(
                title=f"Resposta: {challenge['title']}",
                description=challenge.get('answer', 'Resposta do desafio.'),
                start_date=timezone.make_aware(datetime.datetime.combine(saturday, datetime.time(9, 0))),
                end_date=timezone.make_aware(datetime.datetime.combine(saturday, datetime.time(18, 0))),
                event_type='mystery_answer',
                restaurant=restaurant,
                created_by=self.user,
                color='#10B981',
                event_metadata={'challenge_index': i, 'challenge_event_id': t_event.id},
            )
            created_answers.append(s_event.id)

        return {
            'month': month,
            'year': year,
            'restaurant': restaurant.name,
            'challenges_created': len(created_challenges),
            'answers_created': len(created_answers),
            'challenge_ids': created_challenges,
            'answer_ids': created_answers,
        }
