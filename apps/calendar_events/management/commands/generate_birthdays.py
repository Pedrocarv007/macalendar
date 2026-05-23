"""
Management command: gera eventos de aniversário + cartões para o mês indicado.

Uso:
  python manage.py generate_birthdays
  python manage.py generate_birthdays --month 6 --year 2026
  python manage.py generate_birthdays --month 6 --year 2026 --restaurant-id 3
  python manage.py generate_birthdays --user-email admin@empresa.com

Agendamento sugerido (cron Linux — dia 1 de cada mês às 06:00):
  0 6 1 * * docker exec <container> python manage.py generate_birthdays >> /var/log/macalendar_birthdays.log 2>&1
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.calendar_events.birthday_service import BirthdayService
from apps.core.models import ActivityLog
from apps.restaurants.models import Restaurant


class Command(BaseCommand):
    help = 'Gera eventos de aniversário e cartões PNG para todos os colaboradores do mês.'

    def add_arguments(self, parser):
        now = timezone.now()
        parser.add_argument('--month', type=int, default=now.month,
                            help='Mês alvo (1-12). Default: mês atual.')
        parser.add_argument('--year', type=int, default=now.year,
                            help='Ano alvo. Default: ano atual.')
        parser.add_argument('--restaurant-id', type=int, default=None,
                            help='Limitar a um restaurante específico (PK local). Default: todos.')
        parser.add_argument('--user-email', type=str, default=None,
                            help='Email do utilizador registado como autor dos eventos/cartões.')

    def handle(self, *args, **options):
        month = options['month']
        year = options['year']
        restaurant_id = options['restaurant_id']
        user_email = options['user_email']

        system_user = self._resolve_user(user_email)

        restaurants = Restaurant.objects.filter(is_active=True)
        if restaurant_id:
            restaurants = restaurants.filter(id=restaurant_id)

        if not restaurants.exists():
            self.stdout.write(self.style.WARNING('Nenhum restaurante encontrado.'))
            return

        self.stdout.write(self.style.MIGRATE_HEADING(
            f'A gerar aniversários para {month:02d}/{year} '
            f'({restaurants.count()} restaurante(s))...'
        ))

        service = BirthdayService(user=system_user)
        total_created = 0
        total_skipped = 0

        for restaurant in restaurants:
            result = service.generate_for_month(restaurant, month, year)
            n_created = len(result.get('created', []))
            n_skipped = result.get('skipped', 0)
            total_created += n_created
            total_skipped += n_skipped

            if result.get('error'):
                self.stdout.write(self.style.ERROR(
                    f'  {restaurant.name}: ERRO — {result["error"]}'
                ))
            else:
                self.stdout.write(
                    f'  {restaurant.name}: {n_created} criado(s), {n_skipped} ignorado(s)'
                )

            if n_created > 0:
                ActivityLog.log(
                    'birthdays_generated',
                    f'{n_created} evento(s) de aniversário gerados para {restaurant.name} ({month:02d}/{year})',
                    system_user,
                    restaurant=restaurant,
                )

        self.stdout.write(self.style.SUCCESS(
            f'Concluído: {total_created} evento(s) criado(s), {total_skipped} já existia(m).'
        ))

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
