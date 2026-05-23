from django.db import models


class CalendarEvent(models.Model):
    EVENT_TYPES = [
        ('meeting', 'Reunião'),
        ('birthday', 'Aniversário'),
        ('holiday', 'Feriado'),
        ('shift', 'Turno'),
        ('training', 'Formação'),
        ('post', 'Post'),
        ('mystery_challenge', 'Desafio Mistério'),
        ('mystery_answer', 'Resposta Mistério'),
        ('other', 'Outro'),
    ]

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
    color = models.CharField(max_length=7, default='#3B82F6')
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
