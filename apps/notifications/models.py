from django.db import models


class Notification(models.Model):
    AUDIENCE_CHOICES = [
        ('all', 'Todos'),
        ('manager', 'Gestores'),
        ('employee', 'Colaboradores'),
    ]

    title = models.CharField(max_length=200)
    message = models.TextField(blank=True, default='')
    category = models.CharField(max_length=50, blank=True, default='system')
    audience = models.CharField(max_length=20, choices=AUDIENCE_CHOICES, default='all')

    restaurant = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='notifications',
    )
    user = models.ForeignKey(
        'accounts.Employee',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='notifications',
    )
    created_by = models.ForeignKey(
        'accounts.Employee',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='sent_notifications',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def is_read(self):
        return self.read_at is not None
