from importlib import import_module
from unittest.mock import MagicMock

from django.test import SimpleTestCase


migration = import_module(
    "apps.documents.migrations.0002_drop_stale_worker_fk"
)


class CursorStub:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, sql, params):
        self.calls.append((sql, params))

    def fetchall(self):
        return self.rows


class WorkerConstraintRepairMigrationTests(SimpleTestCase):
    def test_postgresql_worker_constraints_are_discovered_and_dropped(self):
        cursor = CursorStub([
            ("documents_document_worker_id_old_fk",),
        ])
        connection = MagicMock(vendor="postgresql")
        connection.cursor.return_value = cursor
        editor = MagicMock(connection=connection)
        editor.quote_name.side_effect = lambda value: f'"{value}"'

        migration.drop_stale_worker_foreign_keys(None, editor)

        self.assertEqual(
            cursor.calls[0][1],
            ["documents_document", "worker_id"],
        )
        editor.execute.assert_called_once_with(
            'ALTER TABLE "documents_document" DROP CONSTRAINT IF EXISTS '
            '"documents_document_worker_id_old_fk"'
        )

    def test_non_postgresql_databases_are_left_unchanged(self):
        connection = MagicMock(vendor="sqlite")
        editor = MagicMock(connection=connection)

        migration.drop_stale_worker_foreign_keys(None, editor)

        connection.cursor.assert_not_called()
        editor.execute.assert_not_called()
