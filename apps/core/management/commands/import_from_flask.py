"""
Management command: import data from the old Flask PostgreSQL database
into the new Django SQLite database.

Usage:
    python manage.py import_from_flask
"""
import json
import shutil
import warnings
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
import psycopg2
import psycopg2.extras


# ─── Config ────────────────────────────────────────────────────────────────

PG = dict(host='localhost', port=5432, dbname='mcalendar',
          user='TheCarv', password='Carv#2310@76.')

OLD_UPLOADS = Path(r'I:\server_apps\macalendar\app\static\uploads')
NEW_MEDIA   = settings.MEDIA_ROOT

# Role mapping: old Flask roles -> new Django roles
ROLE_MAP = {
    'admin':         'admin',
    'rh':            'rh',
    'marketing':     'marketing',
    'manager':       'gerente_loja',
    'shift_manager': 'gerente_turno',
    'sub_manager':   'sub_gerente',
    'employee':      'employee',
    'rp':            'employee',
    'coucher':       'employee',
}

# Event type mapping
EVENT_TYPE_MAP = {
    'desafio_misterio':          'mystery_challenge',
    'desafio_misterio_resposta': 'mystery_answer',
    'event':                     'other',
    'meeting':                   'meeting',
    'birthday':                  'birthday',
    'holiday':                   'holiday',
    'training':                  'training',
    'post':                      'post',
    'shift':                     'shift',
}

# Document type mapping
DOC_TYPE_MAP = {
    'Aniversário':  'birthday',
    'Aniversario':  'birthday',
    'Anivers�rio':  'birthday',   # encoding artifact
    'Elogio':       'praise',
    'Certificado':  'certificate',
    'Memorando':    'memo',
    'Foto':         'photo',
    'Outros':       'memo',
    'birthday':     'birthday',
    'praise':       'praise',
    'certificate':  'certificate',
    'memo':         'memo',
    'photo':        'photo',
}


def copy_photo(src_rel, dest_subfolder, filename):
    """Copy a photo from old uploads to new media folder."""
    if not filename:
        return
    for subdir in ['employees', 'workers', 'restaurants', '']:
        src = OLD_UPLOADS / subdir / filename if subdir else OLD_UPLOADS / filename
        if src.exists():
            dest = NEW_MEDIA / 'photos' / dest_subfolder
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest / filename)
            return


class Command(BaseCommand):
    help = 'Import data from old Flask PostgreSQL database into Django SQLite'

    def handle(self, *args, **options):
        warnings.filterwarnings('ignore', message='.*received a naive datetime.*')
        self.stdout.write(self.style.MIGRATE_HEADING('Connecting to PostgreSQL...'))
        conn = psycopg2.connect(**PG)
        conn.autocommit = False
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        try:
            with transaction.atomic():
                self._import_restaurants(cur)
                self._import_employees(cur)
                self._import_workers(cur)
                self._import_calendar_events(cur)
                self._import_documents(cur)
                self._import_notifications(cur)
                self._import_tickets(cur)
                self._import_activity_logs(cur)
        finally:
            conn.close()

        self.stdout.write(self.style.SUCCESS('\nOK Import complete!'))

    # ── Restaurants ────────────────────────────────────────────────────────

    def _import_restaurants(self, cur):
        from apps.restaurants.models import Restaurant

        self.stdout.write('  -> Restaurants...', ending='')
        cur.execute('SELECT * FROM restaurants ORDER BY id')
        rows = cur.fetchall()

        Restaurant.objects.all().delete()
        created = 0
        for r in rows:
            Restaurant.objects.create(
                id=r['id'],
                name=r['name'] or '',
                address=r['address'] or '',
                phone=r['phone'] or '',
                email=r['email'] or '',
                capacity=r['capacity'],
                opening_hours=r['opening_hours'] or '',
                description=r['description'] or '',
                photo_filename=r['photo_filename'] or '',
                is_active=r['is_active'] if r['is_active'] is not None else True,
                created_at=r['created_at'],
                updated_at=r['updated_at'],
            )
            copy_photo(None, 'restaurants', r['photo_filename'])
            created += 1

        self.stdout.write(self.style.SUCCESS(f' {created} imported'))

    # ── Employees ──────────────────────────────────────────────────────────

    def _import_employees(self, cur):
        from apps.accounts.models import Employee, UserSettings
        from apps.restaurants.models import Restaurant

        self.stdout.write('  -> Employees...', ending='')
        cur.execute('SELECT * FROM employees ORDER BY id')
        rows = cur.fetchall()

        Employee.objects.all().delete()
        created = 0
        for r in rows:
            old_role = (r['role'] or 'employee').lower()
            new_role = ROLE_MAP.get(old_role, 'employee')
            restaurant = None
            if r['restaurant_id']:
                restaurant = Restaurant.objects.filter(id=r['restaurant_id']).first()

            emp = Employee(
                id=r['id'],
                name=r['name'] or '',
                email=r['email'] or '',
                phone=r['phone'] or '',
                position=r['position'] or '',
                department=r['department'] or '',
                birth_date=r['birth_date'],
                hire_date=r['hire_date'],
                photo_filename=r['photo_filename'] or '',
                restaurant=restaurant,
                is_active=r['is_active'] if r['is_active'] is not None else True,
                address=r['address'] or '',
                notes=r['notes'] or '',
                role=new_role,
                is_staff=(new_role == 'admin'),
                is_superuser=(new_role == 'admin'),
                created_at=r['created_at'],
                updated_at=r['updated_at'],
            )
            emp.set_unusable_password()
            emp.save()
            UserSettings.objects.get_or_create(user=emp)
            copy_photo(None, 'employees', r['photo_filename'])
            created += 1

        self.stdout.write(self.style.SUCCESS(f' {created} imported'))

    # ── Patch restaurant managers ──────────────────────────────────────────

    def _patch_managers(self, cur):
        from apps.restaurants.models import Restaurant
        from apps.accounts.models import Employee

        cur.execute('SELECT id, manager_id FROM restaurants WHERE manager_id IS NOT NULL')
        for r in cur.fetchall():
            emp = Employee.objects.filter(id=r['manager_id']).first()
            if emp:
                Restaurant.objects.filter(id=r['id']).update(manager=emp)

    # ── Workers ────────────────────────────────────────────────────────────

    def _import_workers(self, cur):
        from apps.workers.models import Worker
        from apps.restaurants.models import Restaurant

        self.stdout.write('  -> Workers...', ending='')
        cur.execute('SELECT * FROM workers ORDER BY id')
        rows = cur.fetchall()

        Worker.objects.all().delete()
        created = 0
        for r in rows:
            restaurant = Restaurant.objects.filter(id=r['restaurant_id']).first()
            if not restaurant:
                continue
            Worker.objects.create(
                id=r['id'],
                name=r['name'] or '',
                birth_date=r['birth_date'],
                hire_date=r['hire_date'],
                restaurant=restaurant,
                photo_filename=r['photo_filename'] or '',
                is_active=r['is_active'] if r['is_active'] is not None else True,
                created_at=r['created_at'],
                updated_at=r['updated_at'],
            )
            copy_photo(None, 'workers', r['photo_filename'])
            created += 1

        self.stdout.write(self.style.SUCCESS(f' {created} imported'))

    # ── Calendar Events ────────────────────────────────────────────────────

    def _import_calendar_events(self, cur):
        from apps.calendar_events.models import CalendarEvent
        from apps.restaurants.models import Restaurant
        from apps.accounts.models import Employee

        self.stdout.write('  -> Calendar events...', ending='')
        cur.execute('SELECT * FROM calendar_events ORDER BY id')
        rows = cur.fetchall()

        CalendarEvent.objects.all().delete()
        created = 0
        for r in rows:
            old_type = (r['event_type'] or 'other').lower()
            new_type = EVENT_TYPE_MAP.get(old_type, 'other')

            restaurant = Restaurant.objects.filter(id=r['restaurant_id']).first() if r['restaurant_id'] else None
            created_by = Employee.objects.filter(id=r['created_by']).first() if r['created_by'] else None
            employee   = Employee.objects.filter(id=r['employee_id']).first() if r['employee_id'] else None

            # Parse event_metadata (stored as JSON text in Flask)
            metadata = {}
            if r['event_metadata']:
                try:
                    metadata = json.loads(r['event_metadata'])
                except Exception:
                    metadata = {}

            CalendarEvent.objects.create(
                id=r['id'],
                title=r['title'] or '',
                description=r['description'] or '',
                start_date=r['start_date'],
                end_date=r['end_date'],
                event_type=new_type,
                restaurant=restaurant,
                created_by=created_by,
                employee=employee,
                is_all_day=r['is_all_day'] or False,
                color=r['color'] or '#3B82F6',
                location=r['location'] or '',
                photo_path=r['photo_path'] or '',
                is_recurring=r['is_recurring'] or False,
                recurrence_rule=r['recurrence_rule'] or '',
                event_metadata=metadata,
                created_at=r['created_at'],
                updated_at=r['updated_at'],
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(f' {created} imported'))

    # ── Documents ──────────────────────────────────────────────────────────

    def _import_documents(self, cur):
        from apps.documents.models import Document
        from apps.restaurants.models import Restaurant
        from apps.accounts.models import Employee
        from apps.workers.models import Worker

        self.stdout.write('  -> Documents...', ending='')
        cur.execute('SELECT * FROM documents ORDER BY id')
        rows = cur.fetchall()

        Document.objects.all().delete()
        created = 0
        for r in rows:
            raw_type = r['document_type'] or 'memo'
            new_type = DOC_TYPE_MAP.get(raw_type, DOC_TYPE_MAP.get(raw_type.strip(), 'memo'))

            restaurant = Restaurant.objects.filter(id=r['restaurant_id']).first() if r['restaurant_id'] else None
            if not restaurant:
                continue

            created_by = Employee.objects.filter(id=r['created_by']).first() if r['created_by'] else None
            employee   = Employee.objects.filter(id=r['employee_id']).first() if r['employee_id'] else None
            worker     = Worker.objects.filter(id=r['worker_id']).first() if r.get('worker_id') else None

            Document.objects.create(
                id=r['id'],
                title=r['title'] or '',
                document_type=new_type,
                template_name=r['template_name'] or '',
                employee=employee,
                worker=worker,
                restaurant=restaurant,
                created_by=created_by,
                content=r['content'] or '',
                filename=r['filename'] or '',
                file_path=r['file_path'] or '',
                file_size=r['file_size'],
                file_extension=r['file_extension'] or '',
                description=r['description'] or '',
                tags=r['tags'] or '',
                is_public=r['is_public'] or False,
                status=r['status'] or 'uploaded',
                created_at=r['created_at'],
                updated_at=r['updated_at'],
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(f' {created} imported'))

    # ── Notifications ──────────────────────────────────────────────────────

    def _import_notifications(self, cur):
        from apps.notifications.models import Notification
        from apps.restaurants.models import Restaurant
        from apps.accounts.models import Employee

        self.stdout.write('  -> Notifications...', ending='')
        cur.execute('SELECT * FROM notifications ORDER BY id')
        rows = cur.fetchall()

        Notification.objects.all().delete()
        created = 0
        for r in rows:
            restaurant  = Restaurant.objects.filter(id=r['restaurant_id']).first() if r['restaurant_id'] else None
            user        = Employee.objects.filter(id=r['user_id']).first() if r['user_id'] else None
            created_by  = Employee.objects.filter(id=r['created_by']).first() if r['created_by'] else None

            audience = r['audience'] or 'all'
            if audience not in ['all', 'manager', 'employee']:
                audience = 'all'

            Notification.objects.create(
                id=r['id'],
                title=r['title'] or '',
                message=r['message'] or '',
                category=r['category'] or 'system',
                audience=audience,
                restaurant=restaurant,
                user=user,
                created_by=created_by,
                created_at=r['created_at'],
                read_at=r['read_at'],
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(f' {created} imported'))

    # ── Tickets ────────────────────────────────────────────────────────────

    def _import_tickets(self, cur):
        from apps.tickets.models import Ticket
        from apps.restaurants.models import Restaurant
        from apps.accounts.models import Employee

        self.stdout.write('  -> Tickets...', ending='')
        cur.execute("""
            SELECT id, subject, message, category, priority, status,
                   screenshot_filename, employee_id, restaurant_id,
                   created_at, updated_at, resolved_at
            FROM tickets ORDER BY id
        """)
        rows = cur.fetchall()

        Ticket.objects.all().delete()
        created = 0
        for r in rows:
            employee   = Employee.objects.filter(id=r['employee_id']).first() if r['employee_id'] else None
            restaurant = Restaurant.objects.filter(id=r['restaurant_id']).first() if r['restaurant_id'] else None
            if not employee:
                continue

            Ticket.objects.create(
                id=r['id'],
                subject=r['subject'] or '',
                message=r['message'] or '',
                category=r['category'] or 'other',
                priority=r['priority'] or 'medium',
                status=r['status'] or 'open',
                screenshot_filename=r['screenshot_filename'] or '',
                employee=employee,
                restaurant=restaurant,
                created_at=r['created_at'],
                updated_at=r['updated_at'],
                resolved_at=r['resolved_at'],
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(f' {created} imported'))

    # ── Activity Logs ──────────────────────────────────────────────────────

    def _import_activity_logs(self, cur):
        from apps.core.models import ActivityLog
        from apps.restaurants.models import Restaurant
        from apps.accounts.models import Employee

        self.stdout.write('  -> Activity logs...', ending='')
        cur.execute('SELECT * FROM activity_logs ORDER BY id')
        rows = cur.fetchall()

        ActivityLog.objects.all().delete()
        created = 0

        VALID_TYPES = {c[0] for c in ActivityLog.ACTIVITY_TYPES}

        for r in rows:
            user       = Employee.objects.filter(id=r['user_id']).first() if r['user_id'] else None
            restaurant = Restaurant.objects.filter(id=r['restaurant_id']).first() if r['restaurant_id'] else None

            act_type = r['activity_type'] or 'create'
            if act_type not in VALID_TYPES:
                act_type = 'create'

            ActivityLog.objects.create(
                id=r['id'],
                activity_type=act_type,
                description=r['description'] or '',
                user=user,
                restaurant=restaurant,
                target_id=r['target_id'],
                target_type=r['target_type'] or '',
                created_at=r['created_at'],
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(f' {created} imported'))
