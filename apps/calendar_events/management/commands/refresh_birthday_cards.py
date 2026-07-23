"""
Management command: regenera cartões de aniversário (mês atual + futuros)
com a foto atual de uma ou mais pessoas.

Útil quando a fotografia foi trocada no Portal SSO (o MC não consegue
interceptar essa alteração automaticamente).

Uso:
  python manage.py refresh_birthday_cards --email pedro@empresa.com
  python manage.py refresh_birthday_cards --worker-id 42
  python manage.py refresh_birthday_cards --employee-id 7
  python manage.py refresh_birthday_cards --restaurant-id 3   # todos do restaurante
  python manage.py refresh_birthday_cards --all               # toda a gente (mês atual + futuros)
  python manage.py refresh_birthday_cards --dry-run --email pedro@empresa.com
"""
import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.calendar_events.birthday_service import BirthdayService
from apps.calendar_events.models import CalendarEvent


class Command(BaseCommand):
    help = 'Regenera cartões de aniversário com a foto atual (mês atual + futuros).'

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--email', type=str, default=None,
                           help='Email do colaborador (Worker SSO ou Employee local).')
        group.add_argument('--worker-id', type=int, default=None,
                           help='PK do Worker SSO.')
        group.add_argument('--employee-id', type=int, default=None,
                           help='PK do Employee local.')
        group.add_argument('--restaurant-id', type=int, default=None,
                           help='Regenerar todos os cartões do restaurante (PK local).')
        group.add_argument('--all', dest='all', action='store_true', default=False,
                           help='Regenerar todos os cartões de todos os restaurantes.')
        parser.add_argument('--dry-run', action='store_true', default=False,
                            help='Lista eventos que seriam regenerados sem alterar nada.')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        mode = '[DRY-RUN] ' if dry_run else ''

        today = datetime.date.today()
        first_of_month = today.replace(day=1)
        cutoff = timezone.make_aware(
            datetime.datetime.combine(first_of_month, datetime.time(0, 0))
        )

        service = BirthdayService()

        if options['email']:
            self._by_email(options['email'], service, cutoff, dry_run, mode)
        elif options['worker_id']:
            self._by_ids(worker_id=options['worker_id'], service=service,
                         cutoff=cutoff, dry_run=dry_run, mode=mode)
        elif options['employee_id']:
            self._by_ids(employee_id=options['employee_id'], service=service,
                         cutoff=cutoff, dry_run=dry_run, mode=mode)
        elif options['restaurant_id']:
            self._by_restaurant(options['restaurant_id'], service, cutoff, dry_run, mode)
        elif options['all']:
            from apps.restaurants.services import active_canonical_restaurants
            for rest in active_canonical_restaurants():
                self._by_restaurant(rest.id, service, cutoff, dry_run, mode)

    # ── helpers ──────────────────────────────────────────────────────────────

    def _by_email(self, email, service, cutoff, dry_run, mode):
        from apps.workers.models import Worker
        from apps.accounts.models import Employee

        worker = Worker.objects.filter(email__iexact=email).first()
        employee = Employee.objects.filter(email__iexact=email).first()

        if not worker and not employee:
            self.stdout.write(self.style.ERROR(f'Nenhum colaborador encontrado com email "{email}".'))
            return

        if worker:
            self._by_ids(worker_id=worker.pk, service=service,
                         cutoff=cutoff, dry_run=dry_run, mode=mode, label=worker.name)
        if employee:
            self._by_ids(employee_id=employee.pk, service=service,
                         cutoff=cutoff, dry_run=dry_run, mode=mode, label=employee.name)

    def _by_ids(self, service, cutoff, dry_run, mode,
                worker_id=None, employee_id=None, label=None):
        if worker_id:
            events = CalendarEvent.objects.filter(
                event_type='birthday',
                start_date__gte=cutoff,
                event_metadata__worker_id=worker_id,
            )
        else:
            events = CalendarEvent.objects.filter(
                event_type='birthday',
                start_date__gte=cutoff,
                employee_id=employee_id,
            )

        n = events.count()
        name = label or (f'worker#{worker_id}' if worker_id else f'employee#{employee_id}')
        self.stdout.write(f'{mode}{name}: {n} cartão(ões) a regenerar')

        if not dry_run and n:
            if worker_id:
                service.regenerate_cards_for_person(worker_id=worker_id)
            else:
                service.regenerate_cards_for_person(employee_id=employee_id)
            self.stdout.write(self.style.SUCCESS(f'  ✓ regenerado(s)'))

    def _by_restaurant(self, restaurant_id, service, cutoff, dry_run, mode):
        events = CalendarEvent.objects.filter(
            event_type='birthday',
            restaurant_id=restaurant_id,
            start_date__gte=cutoff,
        )

        # Agrupar por worker_id / employee_id
        worker_ids = set()
        employee_ids = set()
        for ev in events:
            meta = ev.event_metadata or {}
            wid = meta.get('worker_id')
            eid = meta.get('employee_id')
            if wid:
                worker_ids.add(wid)
            elif eid:
                employee_ids.add(eid)

        total = len(worker_ids) + len(employee_ids)
        self.stdout.write(
            f'{mode}Restaurante #{restaurant_id}: '
            f'{total} pessoa(s), {events.count()} cartão(ões)'
        )

        if not dry_run:
            for wid in worker_ids:
                service.regenerate_cards_for_person(worker_id=wid)
            for eid in employee_ids:
                service.regenerate_cards_for_person(employee_id=eid)
            if total:
                self.stdout.write(self.style.SUCCESS(f'  ✓ regenerado(s)'))
