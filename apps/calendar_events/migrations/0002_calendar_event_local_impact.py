from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("calendar_events", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="calendarevent",
            name="event_type",
            field=models.CharField(
                choices=[
                    ("meeting", "Reunião"),
                    ("birthday", "Aniversário"),
                    ("holiday", "Feriado"),
                    ("shift", "Turno"),
                    ("training", "Formação"),
                    ("post", "Post"),
                    ("mystery_challenge", "Desafio Mistério"),
                    ("mystery_answer", "Resposta Mistério"),
                    ("local_impact", "Evento local com impacto"),
                    ("other", "Outro"),
                ],
                db_index=True,
                default="meeting",
                max_length=30,
            ),
        ),
    ]
