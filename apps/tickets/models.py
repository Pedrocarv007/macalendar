from django.db import models


class Ticket(models.Model):
    CATEGORY_CHOICES = [
        ('bug', 'Bug'),
        ('feature', 'Funcionalidade'),
        ('question', 'Questão'),
        ('other', 'Outro'),
    ]
    PRIORITY_CHOICES = [
        ('low', 'Baixa'),
        ('medium', 'Média'),
        ('high', 'Alta'),
        ('critical', 'Crítica'),
    ]
    STATUS_CHOICES = [
        ('open', 'Aberto'),
        ('in_progress', 'Em Progresso'),
        ('resolved', 'Resolvido'),
        ('closed', 'Fechado'),
    ]

    subject = models.CharField(max_length=200)
    message = models.TextField()
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='other')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    screenshot_filename = models.CharField(max_length=255, blank=True, default='')

    employee = models.ForeignKey(
        'accounts.Employee',
        on_delete=models.CASCADE,
        related_name='tickets',
    )
    restaurant = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='tickets',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_status_display()}] {self.subject}"
