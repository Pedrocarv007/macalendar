"""Agendador local da geração de aniversários do MC."""

import time

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        'Executa periodicamente a geração idempotente de aniversários '
        'do mês atual e do mês seguinte.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval-seconds',
            type=int,
            default=21600,
            help='Intervalo entre verificações. Por omissão: 21600 segundos (6 horas).',
        )

    def handle(self, *args, **options):
        interval = max(options['interval_seconds'], 300)
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'Agendador de aniversários MC ativo: verificação a cada {interval} segundos.'
        ))

        while True:
            call_command('generate_birthdays', months_ahead=1)
            self.stdout.write(self.style.SUCCESS(
                f'Próxima verificação de aniversários dentro de {interval} segundos.'
            ))
            time.sleep(interval)
