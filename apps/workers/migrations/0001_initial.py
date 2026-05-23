# Generated migration — workers models are managed=False (read from SSO DB)

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Worker',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(max_length=100)),
                ('last_name', models.CharField(max_length=100)),
                ('employee_number', models.CharField(max_length=20)),
                ('email', models.EmailField(blank=True)),
                ('phone', models.CharField(blank=True, max_length=20)),
                ('birth_date', models.DateField(blank=True, null=True)),
                ('hire_date', models.DateField(blank=True, null=True)),
                ('address', models.TextField(blank=True)),
                ('photo_filename', models.CharField(blank=True, max_length=255)),
                ('notes', models.TextField(blank=True)),
                ('job_role', models.CharField(blank=True, max_length=100)),
                ('restaurant_id', models.IntegerField()),
                ('training_status', models.CharField(blank=True, max_length=20)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField()),
                ('updated_at', models.DateTimeField()),
            ],
            options={
                'db_table': 'Colaboradores',
                'managed': False,
                'ordering': ['first_name', 'last_name'],
            },
        ),
    ]
