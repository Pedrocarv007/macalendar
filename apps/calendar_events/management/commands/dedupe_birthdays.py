"""
Management command: remove eventos de aniversário duplicados causados por pessoas
que existem tanto no SSO (Worker) como como Employee local (mesmo email).

Regra: SSO ganha — apaga o evento baseado em Employee quando existe o equivalente
       baseado em Worker (mesmo restaurante + mesmo mês/ano + mesmo email).

Uso:
  python manage.py dedupe_birthdays --dry-run          # lista duplicados sem apagar
  python manage.py dedupe_birthdays                    # apaga os duplicados de Employee
  python manage.py dedupe_birthdays --month 6 --year 2026
  python manage.py dedupe_birthdays --restaurant-id 3
"""
from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.utils import timezone

from apps.calendar_events.models import CalendarEvent
from apps.restaurants.models import Restaurant
from apps.workers.models import Worker


class Command(BaseCommand):
    help = 'Remove eventos de aniversário duplicados (Worker SSO vs Employee local — SSO ganha).'

    def add_arguments(self, parser):
        now = timezone.now()
        parser.add_argument('--month', type=int, default=None,
                            help='Mês alvo (1-12). Default: todos os meses.')
        parser.add_argument('--year', type=int, default=now.year,
                            help='Ano alvo. Default: ano atual.')
        parser.add_argument('--restaurant-id', type=int, default=None,
                            help='Limitar a um restaurante específico (PK local). Default: todos.')
        parser.add_argument('--dry-run', action='store_true', default=False,
                            help='Lista duplicados sem apagar nada.')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        month = options['month']
        year = options['year']
        restaurant_id = options['restaurant_id']

        mode_label = '[DRY-RUN] ' if dry_run else ''
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'{mode_label}A procurar aniversários duplicados (ano {year}'
            + (f', mês {month:02d}' if month else '')
            + (f', restaurante #{restaurant_id}' if restaurant_id else '')
            + ')...'
        ))

        # ── Eventos de Employee com birth_date no período ─────────────────────
        emp_qs = CalendarEvent.objects.filter(
            event_type='birthday',
            employee__isnull=False,
            start_date__year=year,
        ).select_related('employee', 'restaurant')

        if month:
            emp_qs = emp_qs.filter(start_date__month=month)
        if restaurant_id:
            emp_qs = emp_qs.filter(restaurant_id=restaurant_id)

        total_deleted = 0
        cache_keys_to_clear = set()

        for emp_event in emp_qs:
            emp = emp_event.employee
            if not emp or not emp.email:
                continue

            evt_month = emp_event.start_date.month
            evt_year = emp_event.start_date.year
            restaurant = emp_event.restaurant
            if not restaurant:
                continue

            # Resolver o sso_id do restaurante (Workers usam o SSO id, não o local)
            from apps.workers.models import SSORestaurant
            sso_rest_id = restaurant.sso_id
            if not sso_rest_id:
                sso_rest = SSORestaurant.objects.filter(
                    name__iexact=restaurant.name
                ).first()
                if not sso_rest:
                    sso_rest = SSORestaurant.objects.filter(
                        name__icontains=restaurant.name.split()[0]
                    ).first()
                sso_rest_id = sso_rest.id if sso_rest else None

            if not sso_rest_id:
                continue

            # Verificar se existe Worker com o mesmo email neste restaurante SSO
            worker = Worker.objects.filter(
                email__iexact=emp.email,
                restaurant_id=sso_rest_id,
                is_active=True,
            ).first()

            if not worker:
                continue

            # Confirmar que existe também um evento Worker para o mesmo mês/restaurante
            worker_event_exists = CalendarEvent.objects.filter(
                event_type='birthday',
                restaurant=restaurant,
                start_date__year=evt_year,
                start_date__month=evt_month,
                event_metadata__worker_id=worker.id,
            ).exists()

            if not worker_event_exists:
                continue

            # Duplicado confirmado — o evento de Employee deve ser removido
            # Resolver o Document associado (via event_metadata.document_id)
            meta = emp_event.event_metadata or {}
            doc_id = meta.get('document_id')

            self.stdout.write(
                f'  {"[skip]" if dry_run else "[DEL]"} '
                f'EventoID={emp_event.id} | {emp.name} <{emp.email}> | '
                f'{restaurant.name} {evt_month:02d}/{evt_year}'
                + (f' | Doc#{doc_id}' if doc_id else '')
            )

            if not dry_run:
                cache_keys_to_clear.add(
                    f'bday_ensured:{restaurant.id}:{evt_month}:{evt_year}'
                )
                # Apagar o Document gerado para este evento duplicado
                if doc_id:
                    from apps.documents.models import Document
                    import os as _os
                    try:
                        doc = Document.objects.get(pk=doc_id)
                        # Remover ficheiro PNG do disco se existir
                        if doc.file_path and _os.path.exists(doc.file_path):
                            _os.remove(doc.file_path)
                        doc.delete()
                    except Document.DoesNotExist:
                        pass
                emp_event.delete()
                total_deleted += 1
            else:
                total_deleted += 1  # conta como "seriam removidos"

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'[DRY-RUN] {total_deleted} duplicado(s) encontrado(s) — nada foi apagado.'
            ))
        else:
            # Limpar cache para permitir regeneração limpa na próxima visita ao calendário
            for key in cache_keys_to_clear:
                cache.delete(key)
            self.stdout.write(self.style.SUCCESS(
                f'Concluído: {total_deleted} evento(s) duplicado(s) removido(s). '
                f'{len(cache_keys_to_clear)} chave(s) de cache limpas.'
            ))
