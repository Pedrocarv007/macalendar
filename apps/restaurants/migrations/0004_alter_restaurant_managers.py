from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('restaurants', '0003_restaurant_sso_id')]

    operations = [
        migrations.AlterModelManagers(
            name='restaurant',
            managers=[
                ('objects', models.Manager()),
                ('all_objects', models.Manager()),
            ],
        ),
        migrations.AlterModelOptions(
            name='restaurant',
            options={
                'base_manager_name': 'all_objects',
                'default_manager_name': 'objects',
                'ordering': ['name'],
            },
        ),
    ]
