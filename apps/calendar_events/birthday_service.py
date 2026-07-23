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

        sso_id = self._resolve_sso_id(restaurant, SSORestaurant)

        if not sso_id:
            return {'restaurant': restaurant.name, 'created': [], 'skipped': 0, 'error': 'SSO id não encontrado'}

        workers = Worker.objects.filter(
            is_active=True,
            birth_date__isnull=False,
            birth_date__month=month,
            restaurant_id=sso_id,
        )

        created = []
        repaired = []
        skipped = 0
        cards_with_error = []
        generator = DocumentGenerator()

        for w in workers:
            # Idempotência: manter o evento existente, mas reparar o cartão quando
            # o documento ou o ficheiro PNG associado já não estiver disponível.
            existing_event = CalendarEvent.objects.filter(
                event_type='birthday',
                restaurant=restaurant,
                start_date__year=year,
                start_date__month=month,
                event_metadata__worker_id=w.id,
            ).order_by('id').first()
            if existing_event and self._event_has_available_card(existing_event):
                skipped += 1
                continue

            # Data do aniversário no ano-alvo (proteger 29/02)
            day = w.birth_date.day
            max_day = cal.monthrange(year, month)[1]
            day = min(day, max_day)
            bday = datetime.date(year, month, day)

            # Gerar cartão com a template do restaurante
            document_key = (
                f'birthday:worker:{w.id}:restaurant:{sso_id}:'
                f'year:{year}:month:{month}'
            )
            card = generator.generate(
                'birthday',
                {'worker_id': w.id, 'restaurant_id': restaurant.id, 'person_type': 'worker',
                 'event_year': year, 'document_key': document_key},
                self.user,
            )
            photo_path = card.get('file_url', '') if isinstance(card, dict) and 'file_url' in card else ''
            document_id = card.get('id') if isinstance(card, dict) else None
            card_error = card.get('error') if isinstance(card, dict) else None
            metadata = {
                'worker_id': w.id,
                'document_id': document_id,
                'card_status': 'gerado' if document_id else 'erro',
            }
            if card_error:
                metadata['card_error'] = card_error
                cards_with_error.append({'worker_id': w.id, 'name': w.name, 'error': card_error})

            if existing_event:
                # Limpa referências/documentos incompletos antes de associar o
                # novo resultado ao evento já calendarizado.
                self._delete_event_and_card(existing_event, delete_event=False)
                metadata = {
                    **(existing_event.event_metadata or {}),
                    **metadata,
                }
                existing_event.photo_path = photo_path
                existing_event.event_metadata = metadata
                existing_event.save(update_fields=['photo_path', 'event_metadata'])
                if document_id:
                    repaired.append(existing_event.id)
                else:
                    skipped += 1
                continue

            event = CalendarEvent.objects.create(
                title=f'Aniversário: {w.name}',
                start_date=timezone.make_aware(datetime.datetime.combine(bday, datetime.time(0, 0))),
                is_all_day=True,
                event_type='birthday',
                restaurant=restaurant,
                created_by=self.user,
                color='#FFBC0D',
                photo_path=photo_path,
                event_metadata=metadata,
            )
            created.append(event.id)

        return {
            'restaurant': restaurant.name,
            'created': created,
            'repaired': repaired,
            'skipped': skipped,
            'cards_with_error': cards_with_error,
        }

    @staticmethod
    def _event_has_available_card(event):
        """Confirma que o evento aponta para um documento e PNG existentes."""
        from apps.documents.models import Document

        metadata = event.event_metadata or {}
        document_id = metadata.get('document_id')
        if metadata.get('card_status') != 'gerado' or not document_id:
            return False

        document = Document.objects.filter(pk=document_id).first()
        return bool(
            document
            and document.file_path
            and os.path.isfile(document.file_path)
        )

    def preview_for_month(self, restaurant, month, year):
        """Valida candidatos, fotografias e template sem criar dados."""
        from apps.documents.generators import DocumentGenerator
        from apps.documents.generation.backgrounds import find_template_path
        from apps.documents.generation.config import get_template_definition
        from apps.workers.models import Worker, SSORestaurant

        sso_id = self._resolve_sso_id(restaurant, SSORestaurant)
        if not sso_id:
            return {
                'restaurant': restaurant.name,
                'candidates': 0,
                'ready': 0,
                'missing_photos': [],
                'template_available': False,
                'error': 'ID SSO não encontrado',
            }

        template_path = find_template_path(
            get_template_definition('birthday'),
            restaurant.name,
        )
        workers = list(Worker.objects.filter(
            is_active=True,
            birth_date__isnull=False,
            birth_date__month=month,
            restaurant_id=sso_id,
        ))

        generator = DocumentGenerator()
        missing_photos = []
        for worker in workers:
            status = generator.photo_status({'worker_id': worker.id})
            if not status.get('available'):
                missing_photos.append({
                    'worker_id': worker.id,
                    'name': worker.name,
                })

        return {
            'restaurant': restaurant.name,
            'month': month,
            'year': year,
            'candidates': len(workers),
            'ready': (
                len(workers) - len(missing_photos)
                if template_path is not None
                else 0
            ),
            'missing_photos': missing_photos,
            'template_available': template_path is not None,
            'template_file': template_path.name if template_path else None,
        }

    @staticmethod
    def _resolve_sso_id(restaurant, sso_model):
        if restaurant.sso_id:
            return restaurant.sso_id
        sso_restaurant = sso_model.objects.filter(
            name__iexact=restaurant.name,
            is_active=True,
        ).first()
        return sso_restaurant.id if sso_restaurant else None

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
                        {'worker_id': wkr.id, 'restaurant_id': restaurant.id, 'person_type': 'worker',
                         'event_year': year},
                        self.user,
                    )
                    if isinstance(card, dict) and 'file_url' in card:
                        meta = dict(event.event_metadata or {})
                        meta['document_id'] = card.get('id')
                        meta['card_status'] = 'gerado'
                        meta.pop('card_error', None)
                        event.photo_path = card['file_url']
                        event.event_metadata = meta
                        event.save(update_fields=['photo_path', 'event_metadata'])
                    elif isinstance(card, dict):
                        meta = dict(event.event_metadata or {})
                        meta['card_status'] = 'erro'
                        meta['card_error'] = card.get(
                            'error',
                            'Não foi possível gerar o cartão de aniversário.',
                        )
                        event.event_metadata = meta
                        event.save(update_fields=['event_metadata'])
                fixed += 1

        return {'fixed': fixed}

    def regenerate_cards_for_person(self, *, worker_id=None, employee_id=None):
        """Regenera os cartões futuros depois de uma fotografia ser atualizada."""
        from apps.documents.generators import DocumentGenerator

        if not worker_id and not employee_id:
            raise ValueError('Indique worker_id ou employee_id.')

        first_of_month = datetime.date.today().replace(day=1)
        cutoff = timezone.make_aware(
            datetime.datetime.combine(first_of_month, datetime.time(0, 0))
        )
        events = CalendarEvent.objects.filter(
            event_type='birthday',
            start_date__gte=cutoff,
        ).select_related('restaurant')

        if worker_id:
            events = events.filter(event_metadata__worker_id=worker_id)
            person_data = {
                'worker_id': worker_id,
                'person_type': 'worker',
            }
            person_identifier = f'worker:{worker_id}'
        else:
            events = events.filter(employee_id=employee_id)
            person_data = {
                'employee_id': employee_id,
                'person_type': 'employee',
            }
            person_identifier = f'employee:{employee_id}'

        generator = DocumentGenerator()
        regenerated = 0
        errors = []

        for event in events:
            if event.restaurant is None:
                errors.append({
                    'event_id': event.id,
                    'error': 'O evento não tem restaurante associado.',
                })
                continue

            self._delete_event_and_card(event, delete_event=False)
            restaurant_key = event.restaurant.sso_id or event.restaurant.id
            document_key = (
                f'birthday:{person_identifier}:restaurant:{restaurant_key}:'
                f'year:{event.start_date.year}:month:{event.start_date.month}'
            )
            card = generator.generate(
                'birthday',
                {
                    **person_data,
                    'restaurant_id': event.restaurant.id,
                    'event_year': event.start_date.year,
                    'document_key': document_key,
                },
                self.user,
            )

            metadata = dict(event.event_metadata or {})
            if isinstance(card, dict) and card.get('id'):
                metadata['document_id'] = card['id']
                metadata['card_status'] = 'gerado'
                metadata.pop('card_error', None)
                event.photo_path = card['file_url']
                regenerated += 1
            else:
                error = (
                    card.get('error')
                    if isinstance(card, dict)
                    else 'Não foi possível gerar o cartão de aniversário.'
                )
                metadata['card_status'] = 'erro'
                metadata['card_error'] = error
                errors.append({'event_id': event.id, 'error': error})

            event.event_metadata = metadata
            event.save(update_fields=['photo_path', 'event_metadata'])

        return {
            'regenerated': regenerated,
            'errors': errors,
        }

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
