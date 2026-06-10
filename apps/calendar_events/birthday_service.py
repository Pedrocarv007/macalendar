"""
Geração automática de eventos de aniversário + cartões por restaurante.
Chamado pelo management command generate_birthdays no início de cada mês.
"""
import datetime
import calendar as cal
import logging
import os

from django.utils import timezone

from .models import CalendarEvent

logger = logging.getLogger(__name__)


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

    def sync_date_changes(self, restaurant, month, year, dry_run=False):
        """
        Verifica eventos de aniversário existentes (worker_id) e corrige
        divergências em relação à birth_date actual no SSO.

        - Mês diverge  → apaga evento + documento (generate_birthdays recria no mês certo)
        - Só dia diverge → actualiza start_date + regenera cartão PNG
        - Sem mudança  → skip

        Só age em meses >= mês actual (preserva histórico passado).
        """
        from apps.workers.models import Worker
        from apps.documents.generators import DocumentGenerator
        from apps.documents.models import Document

        today = datetime.date.today()
        if datetime.date(year, month, 1) < today.replace(day=1):
            return {'fixed': 0}

        events = CalendarEvent.objects.filter(
            event_type='birthday',
            restaurant=restaurant,
            start_date__year=year,
            start_date__month=month,
        )

        fixed = 0
        generator = DocumentGenerator() if not dry_run else None

        for event in events:
            worker_id = (event.event_metadata or {}).get('worker_id')
            if not worker_id:
                continue

            try:
                wkr = Worker.objects.get(pk=worker_id, is_active=True)
            except Worker.DoesNotExist:
                continue

            if not wkr.birth_date:
                continue

            # Mês de nascimento diferente do evento → apagar, generate_birthdays recria
            if wkr.birth_date.month != month:
                if not dry_run:
                    self._delete_event_and_card(event)
                fixed += 1
                logger.info('sync_date_changes: worker %d movido de %02d/%d, evento apagado',
                            worker_id, month, year)
                continue

            # Mesmo mês, dia diferente → actualizar data + regenerar cartão
            correct_day = min(wkr.birth_date.day, cal.monthrange(year, month)[1])
            correct_date = datetime.date(year, month, correct_day)
            event_date = event.start_date.date()

            if event_date != correct_date:
                if not dry_run:
                    # Limpar cartão antigo sem apagar o evento
                    self._delete_event_and_card(event, delete_event=False)
                    # Actualizar data
                    event.start_date = timezone.make_aware(
                        datetime.datetime.combine(correct_date, datetime.time(12, 0))
                    )
                    event.save(update_fields=['start_date'])
                    # Regenerar cartão
                    card = generator.generate(
                        'birthday',
                        {'worker_id': wkr.id, 'restaurant_id': restaurant.id, 'person_type': 'worker'},
                        self.user,
                    )
                    if isinstance(card, dict) and 'file_url' in card:
                        meta = dict(event.event_metadata or {})
                        meta['document_id'] = card.get('id')
                        event.photo_path = card['file_url']
                        event.event_metadata = meta
                        event.save(update_fields=['photo_path', 'event_metadata'])
                fixed += 1

        return {'fixed': fixed}

    @staticmethod
    def _delete_event_and_card(event, delete_event=True):
        """Apaga o Document + ficheiro PNG. Se delete_event=False mantém o evento."""
        from apps.documents.models import Document

        doc_id = (event.event_metadata or {}).get('document_id')
        if doc_id:
            try:
                doc = Document.objects.get(pk=doc_id)
                if doc.file_path and os.path.exists(doc.file_path):
                    try:
                        os.remove(doc.file_path)
                    except OSError:
                        pass
                doc.delete()
            except Document.DoesNotExist:
                pass

        if delete_event:
            event.delete()
        else:
            meta = dict(event.event_metadata or {})
            meta.pop('document_id', None)
            event.photo_path = ''
            event.event_metadata = meta
            event.save(update_fields=['photo_path', 'event_metadata'])
