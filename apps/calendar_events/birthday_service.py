"""
Geração automática de eventos de aniversário + cartões por restaurante.
Chamado pelo management command generate_birthdays no início de cada mês.
"""
import datetime
import calendar as cal

from django.utils import timezone

from .models import CalendarEvent


class BirthdayService:

    def __init__(self, user=None):
        self.user = user  # Employee usado como created_by; pode ser None

    def generate_for_month(self, restaurant, month, year):
        """
        Para o restaurante dado, cria um CalendarEvent (birthday) + cartão PNG
        para cada colaborador que faz anos em month/year.

        Retorna {'restaurant': str, 'created': [event_ids], 'skipped': int}.
        """
        from apps.workers.models import Worker, SSORestaurant
        from apps.documents.generators import DocumentGenerator

        # Resolver o SSO restaurant id para filtrar Workers
        sso_id = restaurant.sso_id
        if not sso_id:
            sso_rest = SSORestaurant.objects.filter(
                name__iexact=restaurant.name
            ).first()
            if not sso_rest:
                sso_rest = SSORestaurant.objects.filter(
                    name__icontains=restaurant.name.split()[0]
                ).first()
            sso_id = sso_rest.id if sso_rest else None

        if not sso_id:
            return {'restaurant': restaurant.name, 'created': [], 'skipped': 0, 'error': 'SSO id não encontrado'}

        workers = Worker.objects.filter(
            is_active=True,
            birth_date__isnull=False,
            birth_date__month=month,
            restaurant_id=sso_id,
        )

        created = []
        skipped = 0
        generator = DocumentGenerator()

        for w in workers:
            # Idempotência: saltar se já existe evento para este worker neste mês/ano
            already = CalendarEvent.objects.filter(
                event_type='birthday',
                restaurant=restaurant,
                start_date__year=year,
                start_date__month=month,
                event_metadata__worker_id=w.id,
            ).exists()
            if already:
                skipped += 1
                continue

            # Data do aniversário no ano-alvo (proteger 29/02)
            day = w.birth_date.day
            max_day = cal.monthrange(year, month)[1]
            day = min(day, max_day)
            bday = datetime.date(year, month, day)

            # Gerar cartão com a template do restaurante
            card = generator.generate(
                'birthday',
                {'worker_id': w.id, 'restaurant_id': restaurant.id, 'person_type': 'worker'},
                self.user,
            )
            photo_path = card.get('file_url', '') if isinstance(card, dict) and 'file_url' in card else ''
            document_id = card.get('id') if isinstance(card, dict) else None

            event = CalendarEvent.objects.create(
                title=f'Aniversário: {w.name}',
                start_date=timezone.make_aware(datetime.datetime.combine(bday, datetime.time(0, 0))),
                is_all_day=True,
                event_type='birthday',
                restaurant=restaurant,
                created_by=self.user,
                color='#EC4899',
                photo_path=photo_path,
                event_metadata={'worker_id': w.id, 'document_id': document_id},
            )
            created.append(event.id)

        return {
            'restaurant': restaurant.name,
            'created': created,
            'skipped': skipped,
        }
