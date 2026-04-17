#!/usr/bin/env python3
"""
Audit PostgreSQL DB vs SQLAlchemy models to find unused tables.
Non-destructive: prints a report.
"""
import os
import sys
from pathlib import Path
from io import StringIO
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, MetaData

BASE_DIR = Path(__file__).resolve().parents[1]

# Load .env with encoding fallbacks (same as run.py)
encodings = ('utf-8', 'utf-8-sig', 'utf-16', 'utf-16le', 'utf-16be')
env_path = BASE_DIR / '.env'
if env_path.exists():
    loaded = False
    for enc in encodings:
        try:
            content = env_path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
        else:
            load_dotenv(stream=StringIO(content))
            loaded = True
            break
    if not loaded:
        load_dotenv(env_path)
else:
    load_dotenv(env_path)

# Ensure app is importable
sys.path.insert(0, str(BASE_DIR))

# Import models
from app.models.employee import Employee
from app.models.document import Document
from app.models.calendar_event import CalendarEvent
from app.models.restaurant import Restaurant
from app.models.activity_log import ActivityLog

# Expected tables from models
model_tables = {
    Employee.__tablename__,
    Document.__tablename__,
    CalendarEvent.__tablename__,
    Restaurant.__tablename__,
    ActivityLog.__tablename__,
}

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print('ERROR: DATABASE_URL not set')
    sys.exit(1)

engine = create_engine(DATABASE_URL)
inspector = inspect(engine)

db_tables = set(inspector.get_table_names())

print('--- DB Audit Report ---')
print(f"Database URL: {DATABASE_URL.split('@')[-1]}")
print(f"DB tables ({len(db_tables)}): {sorted(db_tables)}\n")
print(f"Model tables ({len(model_tables)}): {sorted(model_tables)}\n")

orphans = sorted(db_tables - model_tables)
missing = sorted(model_tables - db_tables)

print('Tables present in DB but not in models (candidates to drop):')
if orphans:
    for t in orphans:
        print(f"  - {t}")
else:
    print('  (none)')

print('\nTables defined in models but missing in DB:')
if missing:
    for t in missing:
        print(f"  - {t}")
else:
    print('  (none)')

print('\nDone.')
