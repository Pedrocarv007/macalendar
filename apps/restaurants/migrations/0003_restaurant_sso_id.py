from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('restaurants', '0002_add_nullable_code'),
    ]

    operations = [
        migrations.AddField(
            model_name='restaurant',
            name='sso_id',
            field=models.IntegerField(blank=True, default=None, null=True, unique=True),
        ),
    ]
