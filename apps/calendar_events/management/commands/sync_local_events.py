import time

import requests
from django.core.management.base import BaseCommand, CommandError

from apps.calendar_events.external_events import (
    fetch_tmdb_cinema_releases,
    fetch_visit_oeiras_events,
    sync_external_events,
)


class Command(BaseCommand):
    help = "Sincroniza jogos, eventos da Grande Lisboa e estreias de cinema com impacto."

    def add_arguments(self, parser):
        parser.add_argument("--loop", action="store_true")
        parser.add_argument("--interval-seconds", type=int, default=21600)
        parser.add_argument(
            "--check-only",
            action="store_true",
            help="Confirma as fontes VisitOeiras e cinema sem alterar eventos.",
        )

    def handle(self, *args, **options):
        interval = max(300, options["interval_seconds"])
        if options["check_only"]:
            try:
                events = fetch_visit_oeiras_events()
                cinema_releases = fetch_tmdb_cinema_releases()
            except requests.RequestException as exc:
                raise CommandError(
                    f"A agenda VisitOeiras não respondeu: {exc}"
                ) from exc
            self.stdout.write(
                self.style.SUCCESS(
                    f"VisitOeiras disponível: {len(events)} eventos; "
                    f"cinema: {len(cinema_releases)} estreias de alto impacto."
                )
            )
            return

        while True:
            try:
                result = sync_external_events()
                self.stdout.write(
                    self.style.SUCCESS(
                        "Eventos de movimento: "
                        f'{result["fetched"]} encontrados, '
                        f'{result["relevant"]} relevantes, '
                        f'{result["created"]} novos, '
                        f'{result["updated"]} atualizados. '
                        f'Fontes com erro: {", ".join(result["source_errors"]) or "nenhuma"}.'
                    )
                )
            except requests.RequestException as exc:
                message = f"As agendas externas não responderam: {exc}"
                if not options["loop"]:
                    raise CommandError(message) from exc
                self.stderr.write(self.style.WARNING(message))
            if not options["loop"]:
                break
            time.sleep(interval)
