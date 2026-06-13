"""
Management command: gera eventos de aniversário + cartões para o mês indicado.

Uso:
  python manage.py generate_birthdays
  python manage.py generate_birthdays --month 6 --year 2026
    python manage.py generate_birthdays --months-ahead 1
    python manage.py generate_birthdays --purge-all-existing --months-ahead 1
  python manage.py generate_birthdays --month 6 --year 2026 --restaurant-id 3
  python manage.py generate_birthdays --user-email admin@empresa.com

Agendamento sugerido (cron Linux — dia 1 de cada mês às 06:00):
  0 6 1 * * docker exec <container> python manage.py generate_birthdays >> /var/log/macalendar_birthdays.log 2>&1

Pré-gerar mês atual + próximo mês:
    0 6 1 * * docker exec <container> python manage.py generate_birthdays --months-ahead 1 >> /var/log/macalendar_birthdays.log 2>&1
"""
from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.utils import timezone

from apps.calendar_events.birthday_service import BirthdayService
from apps.calendar_events.models import CalendarEvent
from apps.core.models import ActivityLog
from apps.documents.models import Document
from apps.restaurants.models import Restaurant


class Command(BaseCommand):
    help = 'Gera eventos de aniversário e cartões PNG para todos os colaboradores do mês.'

    def add_arguments(self, parser):
        now = timezone.now()
        parser.add_argument('--month', type=int, default=now.month,
                            help='Mês alvo (1-12). Default: mês atual.')
        parser.add_argument('--year', type=int, default=now.year,
                            help='Ano alvo. Default: ano atual.')
        parser.add_argument('--months-ahead', type=int, default=0,
                    help='Gera também os próximos N meses a partir do mês/ano alvo. Default: 0.')
        parser.add_argument('--purge-all-existing', action='store_true', default=False,
                    help='Apaga todos os aniversários e cartões já gerados antes de recriar a janela pedida.')
        parser.add_argument('--restaurant-id', type=int, default=None,
                            help='Limitar a um restaurante específico (PK local). Default: todos.')
        parser.add_argument('--user-email', type=str, default=None,
                            help='Email do utilizador registado como autor dos eventos/cartões.')
        parser.add_argument('--dry-run', action='store_true', default=False,
                    help='Mostra o que seria apagado/gerado sem gravar alterações.')

    def handle(self, *args, **options):
        month = options['month']
        year = options['year']
        months_ahead = max(options['months_ahead'], 0)
        purge_all_existing = options['purge_all_existing']
        restaurant_id = options['restaurant_id']
        user_email = options['user_email']
        dry_run = options['dry_run']

        system_user = self._resolve_user(user_email)
        months = self._build_month_window(month, year, months_ahead)

        restaurants = Restaurant.objects.filter(is_active=True)
        if restaurant_id:
            restaurants = restaurants.filter(id=restaurant_id)

        if not restaurants.exists():
            self.stdout.write(self.style.WARNING('Nenhum restaurante encontrado.'))
            return

        if purge_all_existing:
            deleted_events, deleted_docs = self._purge_existing_birthdays(restaurants, dry_run=dry_run)
            mode_label = '[DRY-RUN] ' if dry_run else ''
            self.stdout.write(self.style.WARNING(
                f'{mode_label}Limpeza inicial: {deleted_events} evento(s) e {deleted_docs} documento(s) de aniversário '
                f'{"seriam removidos" if dry_run else "removidos"}.'
            ))

        if dry_run:
            total_targets = restaurants.count() * len(months)
            self.stdout.write(self.style.WARNING(
                f'[DRY-RUN] Seriam processados {total_targets} par(es) restaurante/mês para regeneração.'
            ))
            return

        self.stdout.write(self.style.MIGRATE_HEADING(
            f'A gerar aniversários para {len(months)} mês/meses a partir de {month:02d}/{year} '
            f'({restaurants.count()} restaurante(s))...'
        ))

        service = BirthdayService(user=system_user)
        total_created = 0
        total_skipped = 0

        for restaurant in restaurants:
            for target_month, target_year in months:
                result = service.generate_for_month(restaurant, target_month, target_year)
                n_created = len(result.get('created', []))
                n_skipped = result.get('skipped', 0)
                total_created += n_created
                total_skipped += n_skipped

                if result.get('error'):
                    self.stdout.write(self.style.ERROR(
                        f'  {restaurant.name} {target_month:02d}/{target_year}: ERRO — {result["error"]}'
                    ))
                else:
                    self.stdout.write(
                        f'  {restaurant.name} {target_month:02d}/{target_year}: '
                        f'{n_created} criado(s), {n_skipped} ignorado(s)'
                    )

                if n_created > 0:
                    ActivityLog.log(
                        'birthdays_generated',
                        f'{n_created} evento(s) de aniversário gerados para {restaurant.name} '
                        f'({target_month:02d}/{target_year})',
                        system_user,
                        restaurant=restaurant,
                    )

        self.stdout.write(self.style.SUCCESS(
            f'Concluído: {total_created} evento(s) criado(s), {total_skipped} já existia(m).'
        ))

    def _build_month_window(self, month, year, months_ahead):
        months = []
        for offset in range(months_ahead + 1):
            target_month = (month - 1 + offset) % 12 + 1
            target_year = year + (month - 1 + offset) // 12
            months.append((target_month, target_year))
        return months

    def _purge_existing_birthdays(self, restaurants, dry_run=False):
        restaurant_ids = list(restaurants.values_list('id', flat=True))
        events = CalendarEvent.objects.filter(
            event_type='birthday',
            restaurant_id__in=restaurant_ids,
        ).select_related('restaurant')
        linked_doc_ids = set()

        for event in events:
            meta = event.event_metadata or {}
            doc_id = meta.get('document_id')
            if doc_id:
                linked_doc_ids.add(doc_id)

        docs_qs = Document.objects.filter(
            document_type='birthday',
            restaurant_id__in=restaurant_ids,
        )
        all_doc_ids = set(docs_qs.values_list('id', flat=True))
        orphan_doc_ids = all_doc_ids - linked_doc_ids

        deleted_events = events.count()
        deleted_docs = docs_qs.count()

        if dry_run:
            return deleted_events, deleted_docs

        service = BirthdayService(user=None)
        for event in events.iterator():
            service._delete_event_and_card(event, delete_event=True)

        orphan_docs = Document.objects.filter(id__in=orphan_doc_ids)
        for doc in orphan_docs.iterator():
            if doc.file_path:
                from pathlib import Path
                path = Path(doc.file_path)
                if path.exists():
                    try:
                        path.unlink()
                    except OSError:
                        pass
            doc.delete()

        cache.clear()
        return deleted_events, deleted_docs

    def _resolve_user(self, email):
        from apps.accounts.models import Employee
        from django.conf import settings

        if email:
            user = Employee.objects.filter(email=email, is_active=True).first()
            if user:
                return user
            self.stdout.write(self.style.WARNING(f'Utilizador "{email}" não encontrado; a usar system user.'))

        # Primeiro super-role ativo como fallback
        for role in settings.SUPER_ROLES:
            user = Employee.objects.filter(role=role, is_active=True).first()
            if user:
                return user

        return None
