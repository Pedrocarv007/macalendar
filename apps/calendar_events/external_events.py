"""Recolha e análise operacional de eventos com impacto nos restaurantes de Oeiras.

As fontes só dizem *o que* vai acontecer. Este módulo acrescenta a leitura que a
operação precisa: dimensão provável, corredores de regresso, restaurantes
afetados e janelas de pico antes/depois do evento.
"""

from __future__ import annotations

import hashlib
import html
import logging
import os
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone as dt_timezone
from typing import Iterable
from urllib.parse import urljoin

import requests
from django.utils import timezone
from django.utils.html import strip_tags

from apps.restaurants.models import Restaurant

from .models import CalendarEvent


logger = logging.getLogger(__name__)

VISIT_OEIRAS_URL = "https://visitoeiras.com/wp-json/tribe/events/v1/events"
VISIT_LISBOA_URL = "https://www.visitlisboa.com/pt-pt/eventos"
VISIT_CASCAIS_URL = "https://www.visitcascais.com/pt/events"
TMDB_DISCOVER_URL = "https://api.themoviedb.org/3/discover/movie"
TMDB_PUBLIC_MOVIE_URL = "https://www.themoviedb.org/movie"
TMDB_POSTER_BASE_URL = "https://image.tmdb.org/t/p/w780"

DEFAULT_FOOTBALL_ICS_URLS = (
    "https://www.ligaportugal.pt/calendars-ics/estoril_praia.ics",
    "https://www.ligaportugal.pt/calendars-ics/sl_benfica.ics",
    "https://www.ligaportugal.pt/calendars-ics/sporting_cp.ics",
    "https://www.ligaportugal.pt/calendars-ics/casa_pia_ac.ics",
    "https://www.ligaportugal.pt/calendars-ics/estrela_amadora.ics",
)

SOURCE_USER_AGENT = "TheCarv-McCalendar/2.0 (traffic analysis; Oeiras)"
IMPACT_COLORS = {"high": "#DC2626", "medium": "#F59E0B", "low": "#2563EB"}

HIGH_IMPACT_WORDS = (
    "festival", "festa", "arraial", "concerto", "show", "espetaculo",
    "futebol", "jogo", "final", "feira", "maratona", "corrida",
    "torneio", "fogo de artificio", "reveillon", "carnaval", "classico",
    "derby", "mundial", "ironman", "open", "motogp", "formula 1",
    "estreia", "blockbuster",
)
MEDIUM_IMPACT_WORDS = (
    "teatro", "cinema", "musica", "danca", "exposicao", "workshop",
    "oficina", "desporto", "visita", "animacao", "familia", "criancas",
)
MARQUEE_TEAM_WORDS = ("benfica", "sporting", "porto", "selecao", "final")


@dataclass
class ExternalEventCandidate:
    source: str
    source_key: str
    title: str
    start: datetime
    end: datetime | None = None
    description: str = ""
    location: str = ""
    category: str = "other"
    url: str = ""
    image_url: str = ""
    is_all_day: bool = False
    time_confirmed: bool = True
    venue_capacity: int | None = None
    raw: dict = field(default_factory=dict)


# Perfis de recintos e zonas de movimento. As coordenadas servem para auditoria
# e para uma futura ligação a um motor de rotas; a decisão atual usa corredores
# conhecidos (A5, N6/Marginal, CREL/IC19), que são mais estáveis que uma rota
# calculada sem conhecer a morada de cada cliente.
VENUE_PROFILES = {
    "luz": {
        "name": "Estádio da Luz", "zone": "lisbon_core", "capacity": 64642,
        "latitude": 38.7527, "longitude": -9.1848,
        "aliases": ("estadio sl benfica", "estadio da luz"),
    },
    "alvalade": {
        "name": "Estádio José Alvalade", "zone": "lisbon_core", "capacity": 50095,
        "latitude": 38.7610, "longitude": -9.1608,
        "aliases": ("estadio sporting cp", "estadio jose alvalade", "alvalade"),
    },
    "meo_arena": {
        "name": "MEO Arena", "zone": "lisbon_east", "capacity": 20000,
        "latitude": 38.7686, "longitude": -9.0940,
        "aliases": ("meo arena", "altice arena", "pavilhao atlantico"),
    },
    "parque_tejo": {
        "name": "Parque Tejo", "zone": "lisbon_east", "capacity": 80000,
        "latitude": 38.7901, "longitude": -9.0938,
        "aliases": ("parque tejo", "rock in rio lisboa"),
    },
    "fil": {
        "name": "FIL / Parque das Nações", "zone": "lisbon_east", "capacity": 30000,
        "latitude": 38.7718, "longitude": -9.0966,
        "aliases": ("fil lisboa", "feira internacional de lisboa", "parque das nacoes"),
    },
    "terreiro_paco": {
        "name": "Terreiro do Paço", "zone": "lisbon_core", "capacity": 40000,
        "latitude": 38.7077, "longitude": -9.1365,
        "aliases": ("terreiro do paco", "praca do comercio", "lisboa football arena"),
    },
    "alges": {
        "name": "Passeio Marítimo de Algés", "zone": "alges", "capacity": 55000,
        "latitude": 38.6957, "longitude": -9.2354,
        "aliases": ("passeio maritimo de alges", "nos alive", "alges"),
    },
    "jamor": {
        "name": "Complexo Desportivo do Jamor", "zone": "alges", "capacity": 37000,
        "latitude": 38.7087, "longitude": -9.2607,
        "aliases": ("estadio nacional do jamor", "complexo desportivo do jamor", "jamor"),
    },
    "jardins_marques": {
        "name": "Jardins do Marquês de Pombal", "zone": "oeiras_mar", "capacity": 12000,
        "latitude": 38.6915, "longitude": -9.3111,
        "aliases": ("jardins do marques", "palacio do marques", "festival jardins do marques"),
    },
    "marina_oeiras": {
        "name": "Marina de Oeiras", "zone": "oeiras_mar", "capacity": 12000,
        "latitude": 38.6769, "longitude": -9.3172,
        "aliases": ("marina de oeiras", "oeiras marina", "praia da torre", "santo amaro de oeiras"),
    },
    "taguspark": {
        "name": "Taguspark", "zone": "oeiras_a5", "capacity": 10000,
        "latitude": 38.7371, "longitude": -9.3026,
        "aliases": ("taguspark", "tagus park", "porto salvo", "fabrica da polvora"),
    },
    "oeiras_parque": {
        "name": "Oeiras Parque", "zone": "oeiras_internal", "capacity": 15000,
        "latitude": 38.7102, "longitude": -9.3120,
        "aliases": ("oeiras parque", "parque dos poetas"),
    },
    "estoril_stadium": {
        "name": "Estádio António Coimbra da Mota", "zone": "estoril", "capacity": 8015,
        "latitude": 38.7162, "longitude": -9.4064,
        "aliases": ("estadio estoril praia", "estadio antonio coimbra da mota"),
    },
    "estoril_tennis": {
        "name": "Estoril Open", "zone": "cascais", "capacity": 10000,
        "latitude": 38.7086, "longitude": -9.4198,
        "aliases": ("millennium estoril open", "estoril open", "clube de tenis do estoril"),
    },
    "hipodromo_cascais": {
        "name": "Hipódromo Manuel Possolo", "zone": "cascais", "capacity": 18000,
        "latitude": 38.6990, "longitude": -9.4264,
        "aliases": ("hipodromo manuel possolo", "hipodromo de cascais", "cooljazz"),
    },
    "baia_cascais": {
        "name": "Baía de Cascais", "zone": "cascais", "capacity": 40000,
        "latitude": 38.6979, "longitude": -9.4208,
        "aliases": ("baia de cascais", "festas do mar", "marina de cascais"),
    },
    "autodromo_estoril": {
        "name": "Autódromo do Estoril", "zone": "cascais", "capacity": 45000,
        "latitude": 38.7506, "longitude": -9.3942,
        "aliases": ("autodromo do estoril", "estoril classics", "motogp estoril"),
    },
    "casa_pia": {
        "name": "Estádio Casa Pia", "zone": "lisbon_west", "capacity": 7000,
        "latitude": 38.7249, "longitude": -9.2082,
        "aliases": ("estadio casa pia ac", "estadio casa pia", "pina manique"),
    },
    "estrela_amadora": {
        "name": "Estádio José Gomes", "zone": "amadora", "capacity": 9288,
        "latitude": 38.7533, "longitude": -9.2308,
        "aliases": ("estadio estrela amadora", "estadio jose gomes"),
    },
}

# Força do fluxo para cada restaurante (0-100) por zona do evento.
ZONE_RESTAURANT_SCORES = {
    "lisbon_core": {"oeiras_a5": 88, "paco": 78, "oeiras_parque": 70, "tagus": 65, "alges": 68, "oeiras_mar": 58},
    "lisbon_east": {"oeiras_a5": 86, "paco": 76, "oeiras_parque": 68, "tagus": 64, "alges": 65, "oeiras_mar": 55},
    "lisbon_west": {"alges": 92, "oeiras_a5": 82, "paco": 80, "oeiras_mar": 72, "oeiras_parque": 68, "tagus": 64},
    "alges": {"alges": 100, "oeiras_mar": 92, "paco": 84, "oeiras_a5": 80, "oeiras_parque": 70, "tagus": 62},
    "cascais": {"oeiras_mar": 94, "paco": 90, "oeiras_a5": 88, "oeiras_parque": 68, "tagus": 65, "alges": 58},
    "estoril": {"oeiras_mar": 90, "paco": 88, "oeiras_a5": 88, "oeiras_parque": 68, "tagus": 63, "alges": 55},
    "oeiras_mar": {"oeiras_mar": 100, "paco": 92, "oeiras_parque": 82, "oeiras_a5": 74, "alges": 66, "tagus": 60},
    "oeiras_a5": {"tagus": 100, "oeiras_a5": 98, "paco": 90, "oeiras_parque": 84, "oeiras_mar": 62, "alges": 52},
    "oeiras_internal": {"oeiras_parque": 100, "oeiras_a5": 88, "paco": 82, "tagus": 78, "oeiras_mar": 72, "alges": 52},
    "amadora": {"oeiras_a5": 94, "oeiras_parque": 86, "tagus": 82, "paco": 72, "alges": 58, "oeiras_mar": 54},
}

ZONE_CORRIDORS = {
    "lisbon_core": ("A5", "CREL/IC19", "N6/Marginal"),
    "lisbon_east": ("2.ª Circular", "A5", "CREL", "N6/Marginal"),
    "lisbon_west": ("A5", "CRIL", "N6/Marginal"),
    "alges": ("N6/Marginal", "A5", "CRIL"),
    "cascais": ("A5", "N6/Marginal"),
    "estoril": ("A5", "N6/Marginal"),
    "oeiras_mar": ("N6/Marginal", "A5"),
    "oeiras_a5": ("A5", "IC19/CREL"),
    "oeiras_internal": ("A5", "rede interna de Oeiras", "N6/Marginal"),
    "amadora": ("IC19/CREL", "A5"),
}

RESTAURANT_ALIASES = {
    "oeiras_a5": ("oeiras a5", " a5"),
    "oeiras_mar": ("oeiras mar",),
    "paco": ("paco de arcos", "paco"),
    "oeiras_parque": ("oeiras parque",),
    "tagus": ("tagus park", "taguspark", "tagus"),
    "alges": ("alges",),
}

RESTAURANT_ROUTE_REASONS = {
    "oeiras_a5": "absorve diretamente o regresso pela A5 e respetivas saídas de Oeiras",
    "oeiras_mar": "fica no corredor da N6/Marginal e recebe o fluxo costeiro de regresso",
    "paco": "capta a A5/saída de Paço de Arcos e a ligação entre a Marginal e Taguspark",
    "oeiras_parque": "recebe circulação interna do concelho e a redistribuição A5–Oeiras",
    "tagus": "fica junto ao eixo A5/IC19 e ao movimento de Porto Salvo/Taguspark",
    "alges": "é o primeiro ponto da rede no eixo Lisboa–Oeiras pela Marginal/CRIL",
}


def normalize_text(value) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(char for char in text if not unicodedata.combining(char)).lower()


def clean_html(value, *, limit=4000) -> str:
    text = html.unescape(strip_tags(str(value or "")))
    return re.sub(r"\s+", " ", text).strip()[:limit]


def _truthy_env(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return normalize_text(value) not in {"0", "false", "nao", "no", "off"}


def _category_from_text(value: str) -> str:
    text = normalize_text(value)
    if any(word in text for word in ("futebol", "jogo", "torneio", "desporto", "maratona", "ironman", "open")):
        return "sports"
    if any(word in text for word in ("concerto", "musica", "show")):
        return "concert"
    if "festival" in text:
        return "festival"
    if any(word in text for word in ("festa", "arraial", "carnaval", "reveillon")):
        return "local_party"
    if any(word in text for word in ("feira", "mercado")):
        return "fair"
    if any(word in text for word in ("cinema", "filme", "estreia", "movie")):
        return "cinema"
    return "other"


def classify_impact(source_event):
    """Compatibilidade com a regra pública usada pelo formulário e pelos testes."""
    categories = " ".join(item.get("name", "") for item in source_event.get("categories", []))
    tags = " ".join(item.get("name", "") for item in source_event.get("tags", []))
    text = normalize_text(" ".join((source_event.get("title", ""), source_event.get("description", ""), categories, tags)))
    category = _category_from_text(text)
    if any(word in text for word in HIGH_IMPACT_WORDS):
        return "high", category
    if any(word in text for word in MEDIUM_IMPACT_WORDS):
        return "medium", category
    return "low", category


def source_location(source_event) -> str:
    venue = source_event.get("venue") or {}
    parts = (venue.get("venue"), venue.get("address"), venue.get("city"), venue.get("province"), venue.get("zip"))
    return ", ".join(str(part).strip() for part in parts if part)


def parse_source_datetime(value) -> datetime | None:
    if not value:
        return None
    parsed = datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def _month_range(start_date: date, end_date: date):
    current = start_date.replace(day=1)
    while current <= end_date:
        yield current
        current = (current + timedelta(days=32)).replace(day=1)


def _request(client, url, **kwargs):
    headers = {"User-Agent": SOURCE_USER_AGENT, "Accept-Language": "pt-PT,pt;q=0.9"}
    headers.update(kwargs.pop("headers", {}))
    response = client.get(url, timeout=kwargs.pop("timeout", 25), headers=headers, **kwargs)
    response.raise_for_status()
    return response


def fetch_visit_oeiras_events(*, start_date=None, end_date=None, session=None):
    start_date = start_date or timezone.localdate()
    horizon_days = max(1, int(os.getenv("EXTERNAL_EVENTS_HORIZON_DAYS", os.getenv("OEIRAS_EVENTS_HORIZON_DAYS", "180"))))
    end_date = end_date or (start_date + timedelta(days=horizon_days))
    source_url = os.getenv("OEIRAS_EVENTS_API_URL", VISIT_OEIRAS_URL)
    client = session or requests
    events, page = [], 1
    while True:
        payload = _request(
            client,
            source_url,
            timeout=max(3, int(os.getenv("OEIRAS_EVENTS_TIMEOUT_SECONDS", "8"))),
            params={
            "start_date": start_date.isoformat(), "end_date": end_date.isoformat(),
            "per_page": 50, "page": page, "status": "publish",
            },
        ).json()
        events.extend(payload.get("events") or [])
        total_pages = max(1, int(payload.get("total_pages") or 1))
        if page >= total_pages:
            break
        page += 1
    return events


def _visit_oeiras_candidates(events: Iterable[dict]) -> list[ExternalEventCandidate]:
    candidates = []
    for item in events:
        source_id = item.get("id") or item.get("global_id")
        start = parse_source_datetime(item.get("start_date"))
        if not source_id or not start or not item.get("title"):
            continue
        categories = " ".join(part.get("name", "") for part in item.get("categories", []))
        description = clean_html(item.get("description"))
        candidates.append(ExternalEventCandidate(
            source="VisitOeiras", source_key=f"visitoeiras:{source_id}",
            title=clean_html(item["title"], limit=200), start=start,
            end=parse_source_datetime(item.get("end_date")), description=description,
            location=source_location(item), category=_category_from_text(f"{categories} {item['title']} {description}"),
            url=item.get("url", ""), image_url=(item.get("image") or {}).get("url", ""),
            is_all_day=bool(item.get("all_day")), raw=item,
        ))
    return candidates


def fetch_tmdb_cinema_releases(*, start_date=None, end_date=None, session=None):
    """Return high-profile theatrical premieres for the Portuguese market.

    TMDB supports both its API read access token and the legacy v3 API key.
    With neither configured the source is simply inactive, so the other event
    providers continue to sync normally.
    """
    token = os.getenv("TMDB_API_READ_TOKEN", "").strip()
    api_key = os.getenv("TMDB_API_KEY", "").strip()
    if not token and not api_key:
        return []

    start_date = start_date or timezone.localdate()
    end_date = end_date or (
        start_date
        + timedelta(days=max(30, int(os.getenv("CINEMA_RELEASES_HORIZON_DAYS", "120"))))
    )
    minimum_popularity = max(0.0, float(os.getenv("TMDB_MIN_POPULARITY", "20")))
    maximum_releases = max(1, int(os.getenv("TMDB_MAX_RELEASES", "24")))
    maximum_pages = max(1, min(10, int(os.getenv("TMDB_MAX_PAGES", "3"))))
    client = session or requests
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    candidates = []
    page = 1
    while page <= maximum_pages and len(candidates) < maximum_releases:
        params = {
            "include_adult": "false",
            "include_video": "false",
            "language": "pt-PT",
            "region": "PT",
            "page": page,
            "sort_by": "popularity.desc",
            "with_release_type": "3|2",
            "release_date.gte": start_date.isoformat(),
            "release_date.lte": end_date.isoformat(),
        }
        if api_key and not token:
            params["api_key"] = api_key
        payload = _request(
            client,
            os.getenv("TMDB_DISCOVER_URL", TMDB_DISCOVER_URL),
            timeout=max(3, int(os.getenv("TMDB_TIMEOUT_SECONDS", "10"))),
            headers=headers,
            params=params,
        ).json()
        if not isinstance(payload, dict):
            raise ValueError("A resposta TMDB não tem o formato esperado.")

        for item in payload.get("results") or []:
            try:
                movie_id = int(item.get("id"))
                release_date = date.fromisoformat(str(item.get("release_date") or ""))
                popularity = float(item.get("popularity") or 0)
            except (TypeError, ValueError):
                continue
            title = clean_html(item.get("title") or item.get("original_title"), limit=150)
            if not title or popularity < minimum_popularity:
                continue
            release_start = timezone.make_aware(
                datetime.combine(release_date, time.min),
                timezone.get_current_timezone(),
            )
            poster_path = str(item.get("poster_path") or "").strip()
            poster_base = os.getenv("TMDB_POSTER_BASE_URL", TMDB_POSTER_BASE_URL).rstrip("/")
            candidates.append(ExternalEventCandidate(
                source="TMDB",
                source_key=f"tmdb:{movie_id}",
                title=f"Estreia no cinema: {title}",
                start=release_start,
                description=clean_html(item.get("overview")),
                location="Cinemas em Portugal",
                category="cinema",
                url=f"{TMDB_PUBLIC_MOVIE_URL}/{movie_id}",
                image_url=f"{poster_base}/{poster_path.lstrip('/')}" if poster_path else "",
                is_all_day=True,
                time_confirmed=False,
                raw={
                    "force_high_impact": True,
                    "popularity": popularity,
                    "original_title": item.get("original_title") or "",
                    "release_date": release_date.isoformat(),
                    "attribution": (
                        "This product uses the TMDB API but is not endorsed or certified by TMDB."
                    ),
                },
            ))
            if len(candidates) >= maximum_releases:
                break

        total_pages = max(1, min(maximum_pages, int(payload.get("total_pages") or 1)))
        if page >= total_pages:
            break
        page += 1
    return candidates


def _unfold_ics(text: str) -> list[str]:
    unfolded = []
    for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if raw_line.startswith((" ", "\t")) and unfolded:
            unfolded[-1] += raw_line[1:]
        else:
            unfolded.append(raw_line)
    return unfolded


def _ics_unescape(value: str) -> str:
    return value.replace("\\n", "\n").replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\")


def _parse_ics_datetime(value: str) -> tuple[datetime, bool]:
    if len(value) == 8:
        parsed = datetime.strptime(value, "%Y%m%d")
        return timezone.make_aware(parsed, timezone.get_current_timezone()), True
    if value.endswith("Z"):
        parsed = datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=dt_timezone.utc)
    else:
        parsed = datetime.strptime(value, "%Y%m%dT%H%M%S")
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed, False


def _parse_ics_events(text: str, source_url: str) -> list[ExternalEventCandidate]:
    rows, current, candidates = _unfold_ics(text), None, []
    for line in rows:
        if line == "BEGIN:VEVENT":
            current = {}
            continue
        if line == "END:VEVENT":
            if current:
                try:
                    start, date_only = _parse_ics_datetime(current["DTSTART"])
                    end, _ = _parse_ics_datetime(current["DTEND"]) if current.get("DTEND") else (start + timedelta(hours=1, minutes=45), False)
                except (KeyError, ValueError):
                    current = None
                    continue
                local_start = timezone.localtime(start)
                placeholder_time = date_only or (local_start.hour == 0 and local_start.minute == 0)
                if placeholder_time:
                    end = start + timedelta(days=1)
                url = current.get("URL") or source_url
                identity = url if "/match/" in url else current.get("UID", f"{current.get('SUMMARY')}:{current['DTSTART']}")
                source_key = "ligaportugal:" + hashlib.sha1(identity.encode("utf-8")).hexdigest()[:24]
                title = _ics_unescape(current.get("SUMMARY", "Jogo de futebol"))
                candidates.append(ExternalEventCandidate(
                    source="Liga Portugal", source_key=source_key, title=f"Jogo: {title}",
                    start=start, end=end, description=_ics_unescape(current.get("DESCRIPTION", "")),
                    location=_ics_unescape(current.get("LOCATION", "")), category="sports", url=url,
                    is_all_day=placeholder_time, time_confirmed=not placeholder_time,
                    raw={"uid": current.get("UID", ""), "calendar_url": source_url},
                ))
            current = None
            continue
        if current is None or ":" not in line:
            continue
        name, value = line.split(":", 1)
        base_name = name.split(";", 1)[0]
        if base_name in {"UID", "SUMMARY", "DESCRIPTION", "DTSTART", "DTEND", "LOCATION", "URL"}:
            current[base_name] = value.strip()
    return candidates


def fetch_liga_portugal_events(*, start_date=None, end_date=None, session=None):
    start_date = start_date or timezone.localdate()
    horizon = max(30, int(os.getenv("FOOTBALL_EVENTS_HORIZON_DAYS", "180")))
    end_date = end_date or (start_date + timedelta(days=horizon))
    configured = [part.strip() for part in os.getenv("FOOTBALL_ICS_URLS", "").split(",") if part.strip()]
    urls = configured or list(DEFAULT_FOOTBALL_ICS_URLS)
    client, candidates = session or requests, {}
    for url in urls:
        if url.startswith("webcal://"):
            url = "https://" + url[len("webcal://"):]
        text = _request(client, url).text
        for candidate in _parse_ics_events(text, url):
            local_day = timezone.localtime(candidate.start).date()
            if start_date <= local_day <= end_date:
                candidates[candidate.source_key] = candidate
    return list(candidates.values())


def _parse_visit_lisboa_cards(text: str) -> list[dict]:
    cards = []
    link_pattern = re.compile(
        r'<h2[^>]*>\s*<a href="(?P<url>/pt-pt/eventos/[^"]+)"[^>]*>(?P<title>.*?)</a>\s*</h2>',
        re.IGNORECASE | re.DOTALL,
    )
    for match in link_pattern.finditer(text):
        start = max(0, text.rfind('<div data-controller="clickable-card"', 0, match.start()))
        window = text[start:match.end() + 4500]
        times = re.findall(r'<time[^>]+datetime="([^"]+)"', window, re.IGNORECASE)
        if not times:
            continue
        category_matches = re.findall(r'tracking-widest uppercase[^>]*>(.*?)</div>', window[:match.start() - start], re.IGNORECASE | re.DOTALL)
        after_title = window[match.end() - start:]
        description_match = re.search(r'<p[^>]*>(.*?)</p>', after_title, re.IGNORECASE | re.DOTALL)
        image_match = re.search(r'<img[^>]+src="([^"]+)"', window, re.IGNORECASE)
        cards.append({
            "url": match.group("url"), "title": clean_html(match.group("title"), limit=200),
            "dates": times[:2], "category_label": clean_html(category_matches[-1]) if category_matches else "",
            "description": clean_html(description_match.group(1)) if description_match else "",
            "image_url": html.unescape(image_match.group(1)) if image_match else "",
        })
    return cards


def _event_detail_text(client, url: str) -> str:
    text = _request(client, url, timeout=15).text
    marker = re.search(r'>Detalhes</h3>', text, re.IGNORECASE)
    if marker:
        detail_html = text[marker.end():]
        next_section = re.search(r'<h3[^>]*>', detail_html, re.IGNORECASE)
        if next_section:
            detail_html = detail_html[:next_section.start()]
        else:
            detail_html = detail_html[:12000]
        return clean_html(detail_html, limit=6000)
    return ""


def _date_at_local(value: str, *, end=False) -> datetime:
    parsed = date.fromisoformat(value[:10])
    at = time(23, 59, 59) if end else time(0, 0)
    return timezone.make_aware(datetime.combine(parsed, at), timezone.get_current_timezone())


def fetch_visit_lisboa_events(*, start_date=None, end_date=None, session=None):
    start_date = start_date or timezone.localdate()
    horizon = max(30, int(os.getenv("EXTERNAL_EVENTS_HORIZON_DAYS", "180")))
    end_date = end_date or (start_date + timedelta(days=horizon))
    client = session or requests.Session()
    source_url = os.getenv("LISBOA_EVENTS_URL", VISIT_LISBOA_URL)
    params = []
    for category_id in ("77", "79", "81", "82", "83", "151"):
        params.append(("q[categories_id_in][]", category_id))
    for location_id in ("1", "6", "29", "30", "25", "17"):
        params.append(("q[locations_id_in][]", location_id))

    cards_by_url = {}
    max_pages = max(1, int(os.getenv("LISBOA_EVENTS_MAX_PAGES", "6")))
    for page in range(1, max_pages + 1):
        page_params = [*params, ("page", str(page))]
        page_text = _request(client, source_url, params=page_params).text
        page_cards = _parse_visit_lisboa_cards(page_text)
        for card in page_cards:
            cards_by_url[card["url"]] = card
        if not re.search(r'rel="next"', page_text, re.IGNORECASE):
            break

    candidates = []
    load_details = _truthy_env("LISBOA_EVENTS_FETCH_DETAILS", True)
    for card in cards_by_url.values():
        start = _date_at_local(card["dates"][0])
        end = _date_at_local(card["dates"][-1], end=True)
        if end.date() < start_date or start.date() > end_date:
            continue
        absolute_url = urljoin(source_url, card["url"])
        detail = ""
        if load_details:
            try:
                detail = _event_detail_text(client, absolute_url)
            except requests.RequestException as exc:
                logger.warning("Detalhe VisitLisboa indisponível (%s): %s", absolute_url, exc)
        description = " ".join(part for part in (card["description"], detail) if part)
        candidates.append(ExternalEventCandidate(
            source="VisitLisboa", source_key=f"visitlisboa:{card['url'].rstrip('/').split('/')[-1]}",
            title=card["title"], start=start, end=end, description=description,
            category=_category_from_text(f"{card['category_label']} {card['title']} {description}"),
            url=absolute_url, image_url=card["image_url"], is_all_day=True, time_confirmed=False,
            raw={
                "category_label": card["category_label"],
                "listing_description": card["description"],
            },
        ))
    return candidates


ENGLISH_MONTHS = {name: number for number, name in enumerate(
    ("", "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")
)}


def _parse_cascais_date(value: str) -> date:
    match = re.search(r"(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})", value.strip())
    if not match:
        raise ValueError(f"Data VisitCascais inválida: {value}")
    return date(int(match.group(3)), ENGLISH_MONTHS[match.group(2).lower()], int(match.group(1)))


def _parse_visit_cascais_cards(text: str) -> list[dict]:
    pattern = re.compile(
        r'<a[^>]+href="(?P<url>/pt/events/[^"]+)"[^>]*>.*?'
        r'<img[^>]+alt="(?P<title>[^"]+)".*?'
        r'<p class="text-quaternary[^>]*>(?P<dates>.*?)</p>.*?'
        r'<p class="text-sm[^>]*>(?P<description>.*?)</p>',
        re.IGNORECASE | re.DOTALL,
    )
    cards = []
    for match in pattern.finditer(text):
        date_parts = re.split(r"\s+a\s+", clean_html(match.group("dates")), maxsplit=1)
        cards.append({
            "url": match.group("url"), "title": html.unescape(match.group("title")),
            "start_date": _parse_cascais_date(date_parts[0]),
            "end_date": _parse_cascais_date(date_parts[-1]),
            "description": clean_html(match.group("description")),
        })
    return cards


def fetch_visit_cascais_events(*, start_date=None, end_date=None, session=None):
    start_date = start_date or timezone.localdate()
    horizon = max(30, int(os.getenv("EXTERNAL_EVENTS_HORIZON_DAYS", "180")))
    end_date = end_date or (start_date + timedelta(days=horizon))
    client = session or requests.Session()
    source_url = os.getenv("CASCAIS_EVENTS_URL", VISIT_CASCAIS_URL)
    cards = _parse_visit_cascais_cards(_request(client, source_url).text)
    candidates = []
    for card in cards:
        if card["end_date"] < start_date or card["start_date"] > end_date:
            continue
        absolute_url = urljoin(source_url, card["url"])
        detail = ""
        try:
            detail = _event_detail_text(client, absolute_url)
        except requests.RequestException as exc:
            logger.warning("Detalhe VisitCascais indisponível (%s): %s", absolute_url, exc)
        description = " ".join(part for part in (card["description"], detail) if part)
        candidates.append(ExternalEventCandidate(
            source="VisitCascais", source_key=f"visitcascais:{card['url'].rstrip('/').split('/')[-1]}",
            title=card["title"], start=timezone.make_aware(datetime.combine(card["start_date"], time.min), timezone.get_current_timezone()),
            end=timezone.make_aware(datetime.combine(card["end_date"], time.max), timezone.get_current_timezone()),
            description=description, location="Cascais",
            category=_category_from_text(f"{card['title']} {description}"), url=absolute_url,
            is_all_day=True, time_confirmed=False,
            raw={
                "category_label": "Principais eventos",
                "listing_description": card["description"],
            },
        ))
    return candidates


def _venue_profile(candidate: ExternalEventCandidate):
    text = normalize_text(f"{candidate.location} {candidate.title} {candidate.description}")
    best = None
    for key, profile in VENUE_PROFILES.items():
        for alias in profile["aliases"]:
            normalized_alias = normalize_text(alias)
            if normalized_alias in text and (best is None or len(normalized_alias) > best[0]):
                best = (len(normalized_alias), key, profile)
    if best:
        return best[1], best[2]
    if candidate.source == "Liga Portugal":
        # O calendário de cada equipa inclui também os jogos fora. Só entram
        # jogos com correspondência explícita a um estádio da zona analisada.
        return None, None
    fallback_text = normalize_text(
        f"{candidate.location} {candidate.title} "
        f"{candidate.raw.get('listing_description', '')}"
    )
    category_label = normalize_text(candidate.raw.get("category_label", ""))
    explicit_local_place = any(
        word in fallback_text
        for word in ("oeiras", "paco de arcos", "caxias", "porto salvo", "cascais", "estoril", "lisboa")
    )
    movement_signal = (
        candidate.category in {"sports", "festival", "local_party"}
        or "principais eventos" in category_label
        or any(word in fallback_text for word in ("maratona", "ironman", "mundial", "final"))
        or (candidate.category in {"concert", "fair"} and explicit_local_place)
    )
    if not movement_signal:
        return None, None
    if any(word in fallback_text for word in ("oeiras", "paco de arcos", "caxias", "porto salvo")):
        return "generic_oeiras", {"name": candidate.location or "Oeiras", "zone": "oeiras_internal", "capacity": None, "latitude": None, "longitude": None}
    if any(word in fallback_text for word in ("cascais", "estoril")):
        return "generic_cascais", {"name": candidate.location or "Cascais", "zone": "cascais", "capacity": None, "latitude": None, "longitude": None}
    if any(word in fallback_text for word in ("lisboa", "belem", "ajuda", "parque das nacoes")):
        return "generic_lisboa", {"name": candidate.location or "Lisboa", "zone": "lisbon_core", "capacity": None, "latitude": None, "longitude": None}
    return None, None


def _restaurant_key(restaurant) -> str | None:
    text = normalize_text(f"{restaurant.name} {getattr(restaurant, 'address', '')}")
    for key, aliases in RESTAURANT_ALIASES.items():
        if any(alias.strip() in text for alias in aliases):
            return key
    return None


def _event_magnitude(candidate: ExternalEventCandidate, profile: dict) -> float:
    capacity = candidate.venue_capacity or profile.get("capacity")
    category_label = normalize_text(candidate.raw.get("category_label", ""))
    can_fill_venue = (
        candidate.source == "Liga Portugal"
        or candidate.category in {"sports", "festival", "concert", "local_party"}
        or "principais eventos" in category_label
    )
    if not can_fill_venue:
        magnitude = 0.55
    elif capacity and capacity >= 40000:
        magnitude = 1.0
    elif capacity and capacity >= 15000:
        magnitude = 0.92
    elif capacity and capacity >= 7000:
        magnitude = 0.80
    elif capacity and capacity >= 3000:
        magnitude = 0.70
    else:
        text = normalize_text(f"{candidate.title} {candidate.description}")
        magnitude = 0.88 if any(word in text for word in HIGH_IMPACT_WORDS) else 0.64
    if candidate.category in {"festival", "concert", "local_party"}:
        magnitude = min(1.0, magnitude + 0.06)
    if candidate.category == "sports" and any(word in normalize_text(candidate.title) for word in MARQUEE_TEAM_WORDS):
        magnitude = min(1.0, magnitude + 0.10)
    return magnitude


def _impact_level(score: int) -> str:
    if score >= 80:
        return "high"
    if score >= 58:
        return "medium"
    return "low"


def _peak_windows(candidate: ExternalEventCandidate):
    if not candidate.time_confirmed or candidate.is_all_day:
        if candidate.category in {"festival", "concert", "local_party"}:
            label = "Horário oficial por confirmar · picos prováveis 18:00–20:30 e 23:00–01:30"
        else:
            label = "Horário oficial por confirmar · reforçar 90 min antes e até 90 min após o evento"
        return [], label
    end = candidate.end or candidate.start + (timedelta(hours=1, minutes=45) if candidate.category == "sports" else timedelta(hours=3))
    pre_start, pre_end = candidate.start - timedelta(minutes=90), candidate.start - timedelta(minutes=15)
    post_start, post_end = end, end + timedelta(minutes=90)
    windows = [
        {"kind": "pre_event", "label": "Pré-evento", "start": pre_start.isoformat(), "end": pre_end.isoformat()},
        {"kind": "return_home", "label": "Regresso a casa", "start": post_start.isoformat(), "end": post_end.isoformat()},
    ]
    local_pre_start, local_pre_end = timezone.localtime(pre_start), timezone.localtime(pre_end)
    local_post_start, local_post_end = timezone.localtime(post_start), timezone.localtime(post_end)
    label = (
        f"Pré-evento {local_pre_start:%H:%M}–{local_pre_end:%H:%M}; "
        f"regresso {local_post_start:%H:%M}–{local_post_end:%H:%M}"
    )
    return windows, label


def _analyse_cinema_impact(candidate, restaurants):
    """Treat selected national premieres as a deliberate all-store highlight."""
    restaurant_rows = list(restaurants)
    impacts = [
        {
            "restaurant_id": restaurant.id,
            "restaurant_ids": [restaurant.id],
            "restaurant_name": restaurant.name,
            "impact_level": "high",
            "impact_score": 85,
            "corridors": [],
            "reason": "Estreia nacional de cinema com elevada procura esperada.",
        }
        for restaurant in restaurant_rows
    ]
    return {
        "profile_key": "cinema_portugal",
        "venue_name": "Cinemas em Portugal",
        "event_zone": "portugal",
        "latitude": None,
        "longitude": None,
        "venue_capacity": None,
        "impact_level": "high",
        "impact_score": 85,
        "impact_category": "cinema",
        "restaurant_impacts": impacts,
        "matched_restaurant_ids": [restaurant.id for restaurant in restaurant_rows],
        "matched_restaurant_names": [restaurant.name for restaurant in restaurant_rows],
        "corridors": [],
        "route_summary": (
            "Estreia nacional com maior procura esperada durante o primeiro fim de semana."
        ),
        "peak_windows": [],
        "peak_window_label": "Estreia nacional · reforço recomendado no primeiro fim de semana",
    }


def analyse_event_impact(candidate: ExternalEventCandidate, restaurants: Iterable[Restaurant]):
    if candidate.category == "cinema" and candidate.raw.get("force_high_impact"):
        return _analyse_cinema_impact(candidate, restaurants)
    profile_key, profile = _venue_profile(candidate)
    if not profile:
        return None
    zone = profile["zone"]
    route_scores = ZONE_RESTAURANT_SCORES.get(zone, {})
    magnitude = _event_magnitude(candidate, profile)
    restaurant_by_key = {}
    for restaurant in restaurants:
        key = _restaurant_key(restaurant)
        if key:
            restaurant_by_key.setdefault(key, []).append(restaurant)

    corridors = list(ZONE_CORRIDORS.get(zone, ("A5", "N6/Marginal")))
    impacts = []
    for restaurant_key, base_score in route_scores.items():
        equivalent_restaurants = restaurant_by_key.get(restaurant_key, [])
        if not equivalent_restaurants:
            continue
        restaurant = equivalent_restaurants[0]
        score = round(base_score * magnitude)
        if score < 48:
            continue
        level = _impact_level(score)
        impacts.append({
            "restaurant_id": restaurant.id,
            "restaurant_ids": [item.id for item in equivalent_restaurants],
            "restaurant_name": restaurant.name,
            "impact_level": level, "impact_score": score, "corridors": corridors,
            "reason": RESTAURANT_ROUTE_REASONS[restaurant_key],
        })
    impacts.sort(key=lambda item: (-item["impact_score"], item["restaurant_name"]))
    if not impacts or max(item["impact_score"] for item in impacts) < 55:
        return None

    overall_score = max(item["impact_score"] for item in impacts)
    peak_windows, peak_label = _peak_windows(candidate)
    route_summary = (
        f"Movimento de {profile['name']} em direção a Oeiras/Cascais, "
        f"com passagem provável por {', '.join(corridors)}."
    )
    return {
        "profile_key": profile_key, "venue_name": profile["name"], "event_zone": zone,
        "latitude": profile.get("latitude"), "longitude": profile.get("longitude"),
        "venue_capacity": candidate.venue_capacity or profile.get("capacity"),
        "impact_level": _impact_level(overall_score), "impact_score": overall_score,
        "impact_category": candidate.category, "restaurant_impacts": impacts,
        "matched_restaurant_ids": [
            restaurant_id
            for item in impacts
            for restaurant_id in item["restaurant_ids"]
        ],
        "matched_restaurant_names": [item["restaurant_name"] for item in impacts],
        "corridors": corridors, "route_summary": route_summary,
        "peak_windows": peak_windows, "peak_window_label": peak_label,
        "time_confirmed": candidate.time_confirmed,
    }


def match_restaurants(source_event, restaurants):
    """Devolve restaurantes impactados; mantido para integrações antigas."""
    start = parse_source_datetime(source_event.get("start_date")) or timezone.now()
    candidate = ExternalEventCandidate(
        source="manual", source_key="manual", title=source_event.get("title", ""), start=start,
        description=clean_html(source_event.get("description", "")), location=source_location(source_event),
        category=_category_from_text(f"{source_event.get('title', '')} {source_event.get('description', '')}"),
    )
    analysis = analyse_event_impact(candidate, restaurants)
    if not analysis:
        return []
    ids = set(analysis["matched_restaurant_ids"])
    return [restaurant for restaurant in restaurants if restaurant.id in ids]


def _analysis_description(candidate: ExternalEventCandidate, analysis: dict) -> str:
    level_label = {"high": "Alto", "medium": "Médio", "low": "Baixo"}[analysis["impact_level"]]
    restaurant_names = ", ".join(analysis["matched_restaurant_names"])
    source_description = clean_html(candidate.description, limit=2500)
    operational = (
        f"Análise operacional automática — Impacto {level_label}. "
        f"Janela de pico: {analysis['peak_window_label']}. "
        f"Restaurantes mais afetados: {restaurant_names}. {analysis['route_summary']}"
    )
    return f"{source_description}\n\n{operational}".strip()[:4000]


def _candidate_title_tokens(candidate: ExternalEventCandidate) -> set[str]:
    return {
        token for token in re.findall(r"[a-z0-9]+", normalize_text(candidate.title))
        if len(token) >= 4 and token not in {"evento", "festival", "lisboa", "cascais", "oeiras"}
    }


def _same_cross_source_event(left: ExternalEventCandidate, right: ExternalEventCandidate) -> bool:
    if left.source == right.source:
        return False
    if timezone.localtime(left.start).date() != timezone.localtime(right.start).date():
        return False
    left_tokens, right_tokens = _candidate_title_tokens(left), _candidate_title_tokens(right)
    if not left_tokens or not right_tokens:
        return False
    overlap = len(left_tokens & right_tokens) / min(len(left_tokens), len(right_tokens))
    return overlap >= 0.5


def _deduplicate_candidates(candidates: Iterable[ExternalEventCandidate]):
    priority = {"VisitOeiras": 4, "VisitCascais": 3, "VisitLisboa": 2, "Liga Portugal": 1}
    selected = []
    for candidate in candidates:
        duplicate_index = next(
            (index for index, existing in enumerate(selected) if _same_cross_source_event(existing, candidate)),
            None,
        )
        if duplicate_index is None:
            selected.append(candidate)
            continue
        existing = selected[duplicate_index]
        existing_rank = (int(existing.time_confirmed), priority.get(existing.source, 0))
        candidate_rank = (int(candidate.time_confirmed), priority.get(candidate.source, 0))
        chosen, discarded = (candidate, existing) if candidate_rank > existing_rank else (existing, candidate)
        duplicate_keys = set(chosen.raw.get("duplicate_source_keys", []))
        duplicate_keys.update(discarded.raw.get("duplicate_source_keys", []))
        duplicate_keys.add(discarded.source_key)
        chosen.raw["duplicate_source_keys"] = sorted(duplicate_keys - {chosen.source_key})
        selected[duplicate_index] = chosen
    return selected


def _sync_candidates(candidates: Iterable[ExternalEventCandidate], restaurants: list[Restaurant]):
    now_iso = timezone.now().isoformat()
    result = {
        "fetched": 0, "relevant": 0, "created": 0, "updated": 0,
        "removed": 0, "skipped": 0, "suppressed": 0,
    }
    for candidate in candidates:
        result["fetched"] += 1
        source_keys = [
            candidate.source_key,
            *candidate.raw.get("duplicate_source_keys", []),
        ]
        suppressed = False
        for source_key in source_keys:
            stored = CalendarEvent.objects.filter(
                event_type="local_impact",
                event_metadata__source_key=source_key,
            ).first()
            if stored is not None and (stored.event_metadata or {}).get("suppressed"):
                suppressed = True
                break
        if suppressed:
            result["suppressed"] += 1
            continue
        analysis = analyse_event_impact(candidate, restaurants)
        if not analysis:
            result["skipped"] += 1
            obsolete_keys = [candidate.source_key, *candidate.raw.get("duplicate_source_keys", [])]
            for obsolete_key in obsolete_keys:
                obsolete = CalendarEvent.objects.filter(
                    event_type="local_impact",
                    event_metadata__source_key=obsolete_key,
                ).first()
                if obsolete is not None:
                    obsolete.delete()
                    result["removed"] += 1
            continue
        result["relevant"] += 1
        metadata = {
            "external_source": candidate.source, "source_key": candidate.source_key,
            "source_url": candidate.url, "source_synced_at": now_iso,
            "duplicate_source_keys": candidate.raw.get("duplicate_source_keys", []),
            **analysis, "coverage": "affected_restaurants",
        }
        values = {
            "title": candidate.title[:200], "description": _analysis_description(candidate, analysis),
            "start_date": candidate.start, "end_date": candidate.end, "event_type": "local_impact",
            "restaurant": None, "is_all_day": candidate.is_all_day,
            "color": IMPACT_COLORS[analysis["impact_level"]],
            "location": (candidate.location or analysis["venue_name"])[:200],
            "photo_path": candidate.image_url[:300], "link": candidate.url[:200],
            "event_metadata": metadata,
        }
        event = CalendarEvent.objects.filter(
            event_type="local_impact", event_metadata__source_key=candidate.source_key,
        ).first()
        if event is None:
            event = CalendarEvent.objects.create(**values)
            result["created"] += 1
        else:
            for name, value in values.items():
                setattr(event, name, value)
            event.save(update_fields=[*values.keys(), "updated_at"])
            result["updated"] += 1
        event.affected_restaurants.set(analysis["matched_restaurant_ids"])
        for duplicate_key in candidate.raw.get("duplicate_source_keys", []):
            duplicate = CalendarEvent.objects.filter(
                event_type="local_impact",
                event_metadata__source_key=duplicate_key,
            ).first()
            if duplicate is not None:
                duplicate.delete()
                result["removed"] += 1
    return result


def sync_visit_oeiras_events(*, start_date=None, end_date=None, session=None):
    """Compatibilidade: sincroniza apenas a fonte VisitOeiras."""
    raw_events = fetch_visit_oeiras_events(start_date=start_date, end_date=end_date, session=session)
    restaurants = list(Restaurant.objects.filter(is_active=True).order_by("name"))
    return _sync_candidates(_visit_oeiras_candidates(raw_events), restaurants)


def sync_external_events(*, start_date=None, end_date=None, session=None):
    start_date = start_date or timezone.localdate()
    horizon = max(30, int(os.getenv("EXTERNAL_EVENTS_HORIZON_DAYS", "180")))
    end_date = end_date or (start_date + timedelta(days=horizon))
    enabled = {
        normalize_text(item).replace("-", "_").strip()
        for item in os.getenv(
            "EXTERNAL_EVENT_SOURCES", "liga_portugal,visit_oeiras,visit_lisboa,visit_cascais,tmdb"
        ).split(",") if item.strip()
    }
    providers = (
        ("liga_portugal", "Liga Portugal", fetch_liga_portugal_events),
        ("visit_oeiras", "VisitOeiras", lambda **kwargs: _visit_oeiras_candidates(fetch_visit_oeiras_events(**kwargs))),
        ("visit_lisboa", "VisitLisboa", fetch_visit_lisboa_events),
        ("visit_cascais", "VisitCascais", fetch_visit_cascais_events),
        ("tmdb", "TMDB Cinema", fetch_tmdb_cinema_releases),
    )
    candidates, source_results, errors = [], {}, []
    for provider_key, source_name, provider in providers:
        if provider_key not in enabled:
            continue
        try:
            source_candidates = provider(start_date=start_date, end_date=end_date, session=session)
            candidates.extend(source_candidates)
            source_results[source_name] = {"fetched": len(source_candidates), "status": "ok"}
        except (requests.RequestException, ValueError, KeyError) as exc:
            logger.warning("Fonte de eventos %s indisponível: %s", source_name, exc)
            source_results[source_name] = {"fetched": 0, "status": "error", "error": str(exc)[:300]}
            errors.append(source_name)

    deduplicated = _deduplicate_candidates(candidates)
    restaurants = list(Restaurant.objects.filter(is_active=True).order_by("name"))
    result = _sync_candidates(deduplicated, restaurants)
    result.update({"sources": source_results, "source_errors": errors})
    logger.info("Sincronização de eventos externos concluída: %s", result)
    return result
