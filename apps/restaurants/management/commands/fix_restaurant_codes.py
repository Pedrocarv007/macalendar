"""
Management command: corrige os códigos e nomes dos restaurantes.

O banco SSO é a fonte de verdade; o banco local sincroniza a partir dele.
Este command:
  1. Atualiza code/name no banco SSO ("Restaurants").
  2. Remaeia FKs locais órfãs (restaurant_id 2 → 5).
  3. Apaga linhas locais órfãs (ids 1, 2, 4).
  4. Sincroniza code/name nas linhas canónicas locais imediatamente.

Uso:
    python manage.py fix_restaurant_codes           # aplica
    python manage.py fix_restaurant_codes --dry-run # só mostra o que faria
"""
import psycopg2
import psycopg2.extras
from django.core.management.base import BaseCommand
from django.db import transaction


# ── Configuração ──────────────────────────────────────────────────────────────

PG_SSO = dict(
    host='localhost', port=5432,
    dbname='SSO_TheCarv_Carlos_Cardoso',
    user='TheCarv', password='Carv#2310@76.',
    options='-c client_encoding=UTF8',
)

PG_LOCAL = dict(
    host='localhost', port=5432,
    dbname='mcalendar_new',
    user='TheCarv', password='Carv#2310@76.',
    options='-c client_encoding=UTF8',
)

# SSO id → (novo code, novo name ou None para manter)
SSO_UPDATES = {
    2: ('REMASO',   None),            # Oeiras A5 — mantém nome
    3: ('RM5O',     'Oeiras'),        # Oeiras Mar → Oeiras
    4: ('Resiparc', None),            # Oeiras Parque — mantém nome
    5: ('RMCX',     None),            # Tagus Park — mantém nome
    8: ('REPA',     'Paço de Arcos'), # corrigir acento
    9: ('Alfragés', 'Algés'),         # corrigir acento + code
}

# FKs locais a remapear: restaurant_id antigo → canónico
FK_REMAP = {2: 5}

# Tabelas locais com restaurant_id que precisam de remap
FK_TABLES = [
    'accounts_employee',
    'core_activitylog',
    'documents_document',
    'calendar_events_calendarevent',
    'notifications_notification',
    'tickets_ticket',
]

# Ids locais a apagar depois do remap (sem referências ou duplicados)
LOCAL_ORPHAN_IDS = [1, 2, 4]


class Command(BaseCommand):
    help = 'Corrige códigos/nomes dos restaurantes no SSO e limpa duplicados locais'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=False,
            help='Mostra o que seria feito sem escrever nada',
        )

    def handle(self, *args, **options):
        dry = options['dry_run']
        tag = '[DRY-RUN] ' if dry else ''

        self.stdout.write(self.style.MIGRATE_HEADING(
            f'\n{"=" * 60}\n  fix_restaurant_codes  {tag}\n{"=" * 60}'
        ))

        # ── 1. SSO ────────────────────────────────────────────────
        self._step_sso(dry, tag)

        # ── 2-4. Local ────────────────────────────────────────────
        self._step_local(dry, tag)

        if dry:
            self.stdout.write(self.style.WARNING('\n[DRY-RUN] Nenhuma alteração foi escrita.'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✓ Concluído com sucesso.'))

    # ── SSO ───────────────────────────────────────────────────────────────────

    def _step_sso(self, dry, tag):
        self.stdout.write('\n' + self.style.MIGRATE_LABEL('Passo 1 — Banco SSO'))
        conn = psycopg2.connect(**PG_SSO)
        conn.autocommit = False
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        try:
            cur.execute('SELECT id, code, name FROM "Restaurants" ORDER BY id')
            rows = {r['id']: r for r in cur.fetchall()}

            changes = []
            for sso_id, (new_code, new_name) in SSO_UPDATES.items():
                row = rows.get(sso_id)
                if not row:
                    self.stdout.write(
                        self.style.WARNING(f'  AVISO: SSO id {sso_id} não encontrado — ignorado')
                    )
                    continue

                old_code = row['code']
                old_name = row['name']
                final_name = new_name if new_name else old_name

                changed = (old_code != new_code) or (new_name and old_name != new_name)
                if not changed:
                    self.stdout.write(f'  id {sso_id:2d}: já correto ({old_code} / {old_name})')
                    continue

                self.stdout.write(
                    f'  {tag}id {sso_id:2d}: '
                    f'code {old_code!r:>10} → {new_code!r:<10}  '
                    f'name {old_name!r} → {final_name!r}'
                )
                if not dry:
                    cur.execute(
                        'UPDATE "Restaurants" SET code=%s, name=%s WHERE id=%s',
                        (new_code, final_name, sso_id),
                    )
                changes.append(sso_id)

            if not dry:
                conn.commit()
                self.stdout.write(self.style.SUCCESS(f'  SSO: {len(changes)} linha(s) atualizada(s)'))
            else:
                conn.rollback()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ── Local ─────────────────────────────────────────────────────────────────

    def _step_local(self, dry, tag):
        conn = psycopg2.connect(**PG_LOCAL)
        conn.autocommit = False
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        try:
            # ── 2. Remap FKs ──────────────────────────────────────
            self.stdout.write('\n' + self.style.MIGRATE_LABEL('Passo 2 — Remapear FKs locais'))
            for old_id, new_id in FK_REMAP.items():
                for table in FK_TABLES:
                    cur.execute(
                        f'SELECT count(*) AS n FROM {table} WHERE restaurant_id=%s',
                        (old_id,),
                    )
                    n = cur.fetchone()['n']
                    if n == 0:
                        continue
                    self.stdout.write(
                        f'  {tag}{table}: {n} linha(s) restaurant_id {old_id} → {new_id}'
                    )
                    if not dry:
                        cur.execute(
                            f'UPDATE {table} SET restaurant_id=%s WHERE restaurant_id=%s',
                            (new_id, old_id),
                        )

            # ── 3. Apagar órfãos ───────────────────────────────────
            self.stdout.write('\n' + self.style.MIGRATE_LABEL('Passo 3 — Apagar linhas locais órfãs'))
            cur.execute(
                'SELECT id, code, name, sso_id FROM restaurants_restaurant WHERE id = ANY(%s)',
                (LOCAL_ORPHAN_IDS,),
            )
            orphans = cur.fetchall()
            if orphans:
                for o in orphans:
                    self.stdout.write(
                        f'  {tag}Apagar local id {o["id"]:2d}: '
                        f'code={o["code"]!r}, name={o["name"]!r}, sso_id={o["sso_id"]}'
                    )
                if not dry:
                    cur.execute(
                        'DELETE FROM restaurants_restaurant WHERE id = ANY(%s)',
                        (LOCAL_ORPHAN_IDS,),
                    )
            else:
                self.stdout.write('  Nenhum órfão encontrado (já limpos).')

            # ── 4. Sincronizar código/nome local imediatamente ─────
            self.stdout.write('\n' + self.style.MIGRATE_LABEL('Passo 4 — Sincronizar local com novos valores'))
            # Buscar estado atual do SSO (já atualizado no passo 1, ou em dry-run o que deveria ser)
            sso_conn = psycopg2.connect(**PG_SSO)
            sso_cur = sso_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            try:
                sso_cur.execute(
                    'SELECT id, code, name FROM "Restaurants" WHERE id = ANY(%s)',
                    (list(SSO_UPDATES.keys()),),
                )
                sso_rows = {r['id']: r for r in sso_cur.fetchall()}
            finally:
                sso_conn.close()

            for sso_id in SSO_UPDATES:
                new_code, new_name = SSO_UPDATES[sso_id]
                # Em dry-run usamos os valores pretendidos; em run real usamos o que está no SSO
                if dry:
                    sso_row = sso_rows.get(sso_id, {})
                    # Em dry-run o SSO ainda tem valores antigos; mostramos o que ficaria
                    target_code = new_code
                    target_name = new_name if new_name else (sso_row.get('name', ''))
                else:
                    sso_row = sso_rows.get(sso_id, {})
                    target_code = sso_row.get('code', new_code)
                    target_name = sso_row.get('name', new_name or '')

                cur.execute(
                    'SELECT id, code, name FROM restaurants_restaurant WHERE sso_id=%s',
                    (sso_id,),
                )
                local = cur.fetchone()
                if not local:
                    self.stdout.write(
                        f'  AVISO: nenhuma linha local com sso_id={sso_id} — '
                        f'será criada pelo sync da view'
                    )
                    continue

                old_lcode = local['code']
                old_lname = local['name']
                if old_lcode == target_code and old_lname == target_name:
                    self.stdout.write(f'  local id {local["id"]}: já sincronizado')
                    continue

                self.stdout.write(
                    f'  {tag}local id {local["id"]:2d} (sso_id={sso_id}): '
                    f'code {old_lcode!r} → {target_code!r}, '
                    f'name {old_lname!r} → {target_name!r}'
                )
                if not dry:
                    cur.execute(
                        'UPDATE restaurants_restaurant SET code=%s, name=%s WHERE id=%s',
                        (target_code, target_name, local['id']),
                    )

            if not dry:
                conn.commit()
                self.stdout.write(self.style.SUCCESS('\n  Local: alterações confirmadas.'))
            else:
                conn.rollback()

        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
