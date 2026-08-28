from django.db import migrations


DOCUMENTS_TABLE = "documents_document"
WORKER_COLUMN = "worker_id"


def drop_stale_worker_foreign_keys(apps, schema_editor):
    """Remove constraints locais inválidas sobre IDs de workers do SSO.

    ``workers.Worker`` é um modelo read-only encaminhado para a base ``sso``.
    Por isso ``Document.worker`` usa ``db_constraint=False``. Algumas bases de
    produção foram criadas antes dessa opção e conservaram uma FK PostgreSQL
    para uma tabela local inexistente/desatualizada, bloqueando a geração de
    cartões para colaboradores do Portal.
    """
    connection = schema_editor.connection
    if connection.vendor != "postgresql":
        return

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT tc.constraint_name
            FROM information_schema.table_constraints AS tc
            INNER JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_schema = kcu.constraint_schema
             AND tc.constraint_name = kcu.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema = current_schema()
              AND tc.table_name = %s
              AND kcu.column_name = %s
            """,
            [DOCUMENTS_TABLE, WORKER_COLUMN],
        )
        constraint_names = [row[0] for row in cursor.fetchall()]

    table = schema_editor.quote_name(DOCUMENTS_TABLE)
    for constraint_name in constraint_names:
        constraint = schema_editor.quote_name(constraint_name)
        schema_editor.execute(
            f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {constraint}"
        )


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            drop_stale_worker_foreign_keys,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
