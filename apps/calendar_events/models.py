from django.db import models


class CalendarEvent(models.Model):
    # Legacy values remain valid for historical rows and imports, but they are
    # no longer offered as filters or creation choices in the calendar UI.
    HIDDEN_EVENT_TYPE_OPTIONS = {
        'shift', 'training', 'mystery_challenge', 'mystery_answer',
    }
    EVENT_TYPES = [
        ('meeting', 'Reunião'),
        ('birthday', 'Aniversário'),
        ('holiday', 'Feriado'),
        ('shift', 'Turno'),
        ('training', 'Formação'),
        ('post', 'Post'),
        ('mystery_challenge', 'Desafio Mistério'),
        ('mystery_answer', 'Resposta Mistério'),
        ('local_impact', 'Evento local com impacto'),
        ('other', 'Outro'),
    ]

    # One stable colour per event type.  The colour is part of the calendar's
    # visual language, not a per-event preference; keeping it here prevents
    # the web UI, imports and scheduled jobs from drifting apart.
    EVENT_COLORS = {
        'meeting': '#93C5FD',
        'birthday': '#FFBC0D',
        'holiday': '#FCA5A5',
        'shift': '#CBD5E1',
        'training': '#99F6E4',
        'post': '#F9A8D4',
        'mystery_challenge': '#C4B5FD',
        'mystery_answer': '#86EFAC',
        'local_impact': '#FDBA74',
        'other': '#D4D4D8',
    }

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    start_date = models.DateTimeField(db_index=True)
    end_date = models.DateTimeField(null=True, blank=True)
    event_type = models.CharField(max_length=30, choices=EVENT_TYPES, default='meeting', db_index=True)

    # Scope: null = all restaurants (global)
    restaurant = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='events',
    )
    # Eventos externos podem afetar vários restaurantes sem serem duplicados.
    # ``restaurant`` continua a ser o âmbito dos eventos criados manualmente.
    affected_restaurants = models.ManyToManyField(
        'restaurants.Restaurant',
        blank=True,
        related_name='traffic_impact_events',
    )
    created_by = models.ForeignKey(
        'accounts.Employee',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_events',
    )
    # For birthday events linked to a specific employee/worker
    employee = models.ForeignKey(
        'accounts.Employee',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='birthday_events',
    )

    is_all_day = models.BooleanField(default=False)
    color = models.CharField(max_length=7, default=EVENT_COLORS['meeting'])
    location = models.CharField(max_length=200, blank=True, default='')
    photo_path = models.CharField(max_length=300, blank=True, default='')
    link = models.URLField(blank=True, default='')

    # Recurrence
    is_recurring = models.BooleanField(default=False)
    recurrence_rule = models.CharField(max_length=500, blank=True, default='')

    # Extra metadata (JSON)
    event_metadata = models.JSONField(default=dict, blank=True)

    # Post tracking
    is_posted = models.BooleanField(default=False)
    posted_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start_date']
        indexes = [
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['event_type']),
            models.Index(fields=['restaurant']),
        ]

    def __str__(self):
        return f"{self.title} ({self.start_date.date()})"

    @classmethod
    def color_for_type(cls, event_type):
        return cls.EVENT_COLORS.get(event_type, cls.EVENT_COLORS['other'])

    @classmethod
    def event_type_options(cls):
        return [
            {
                'value': value,
                'label': label,
                'color': cls.color_for_type(value),
            }
            for value, label in cls.EVENT_TYPES
            if value not in cls.HIDDEN_EVENT_TYPE_OPTIONS
        ]

    def save(self, *args, **kwargs):
        self.color = self.color_for_type(self.event_type)
        update_fields = kwargs.get('update_fields')
        if update_fields is not None:
            kwargs['update_fields'] = set(update_fields) | {'color'}
        return super().save(*args, **kwargs)
