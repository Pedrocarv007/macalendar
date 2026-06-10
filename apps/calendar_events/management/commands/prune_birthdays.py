"""
Management command: remove eventos de aniversário de colaboradores
desativados/apagados para o mês atual e meses futuros.
Eventos de meses passados são sempre preservados (histórico).

Uso:
  python manage.py prune_birthdays                          # mês atual + 2 meses futuros
  python manage.py prune_birthdays --months-ahead 5        # mês atual + 5 meses futuros
  python manage.py prune_birthdays --dry-run               # lista sem apagar
  python manage.py prune_birthdays --restaurant-id 3       # só um restaurante
"""
from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.utils import timezone

from apps.calendar_events.birthday_service import BirthdayService
from apps.restaurants.models import Restaurant


class Command(BaseCommand):
    help = 'Remove aniversários de colaboradores inativos/apagados (mês atual + futuros).'

    def add_arguments(self, parser):
        parser.add_argument('--months-ahead', type=int, default=2,
                            help='Quantos meses futuros além do atual verificar. Default: 2.')
        parser.add_argument('--restaurant-id', type=int, default=None,
                            help='Limitar a um restaurante (PK local). Default: todos.')
        parser.add_argument('--dry-run', action='store_true', default=False,
                            help='Lista eventos removíveis sem apagar nada.')

    def handle(self, *args, **options):
        months_ahead = options['months_ahead']
        restaurant_id = options['restaurant_id']
        dry_run = options['dry_run']

        mode = '[DRY-RUN] ' if dry_run else ''
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'{mode}A verificar aniversários de inativos '
            f'(mês atual + {months_ahead} mês/meses)...'
        ))

        now = timezone.now()
        # Montar lista de (month, year) a verificar
        months = []
        cur_month = now.month
        cur_year = now.year
        for i in range(months_ahead + 1):
            m = (cur_month - 1 + i) % 12 + 1
            y = cur_year + (cur_month - 1 + i) // 12
            months.append((m, y))

        restaurants = Restaurant.objects.filter(is_active=True)
        if restaurant_id:
            restaurants = restaurants.filter(id=restaurant_id)

        if not restaurants.exists():
            self.stdout.write(self.style.WARNING('Nenhum restaurante encontrado.'))
            return

        service = BirthdayService()
        total_stale = 0
        cache_keys_to_clear = set()

        for restaurant in restaurants:
            for month, year in months:
                result = service.prune_inactive(restaurant, month, year, dry_run=dry_run)
                n = len(result['stale'])
                if n:
                    total_stale += n
                    label = 'encontrado(s)' if dry_run else 'removido(s)'
                    self.stdout.write(
                        f'  {restaurant.name} {month:02d}/{year}: '
                        f'{n} evento(s) {label}'
                    )
                    if not dry_run:
                        cache_keys_to_clear.add(
                            f'bday_ensured:{restaurant.id}:{month}:{year}'
                        )

        if not dry_run:
            for key in cache_keys_to_clear:
                cache.delete(key)

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'[DRY-RUN] {total_stale} evento(s) seriam removidos — nada foi apagado.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'Concluído: {total_stale} evento(s) de inativos removido(s). '
                f'{len(cache_keys_to_clear)} chave(s) de cache limpas.'
            ))
