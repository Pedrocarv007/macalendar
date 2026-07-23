"""
Core models — ActivityLog for audit trail.
"""
from django.db import models
from django.conf import settings


class ActivityLog(models.Model):
    """
    Audit log for all significant actions in the system.
    """
    ACTIVITY_TYPES = [
        ('login', 'Entrada'),
        ('logout', 'Saída'),
        ('create', 'Criação'),
        ('update', 'Atualização'),
        ('delete', 'Eliminação'),
        ('view', 'Consulta'),
        ('upload', 'Carregamento'),
        ('download', 'Transferência'),
        ('generate', 'Geração'),
        ('send', 'Envio'),
        ('reset_password', 'Reposição da palavra-passe'),
        ('status_change', 'Alteração de estado'),
        ('error', 'Erro'),
    ]

    activity_type = models.CharField(max_length=50, choices=ACTIVITY_TYPES)
    description = models.TextField()
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activity_logs',
    )
    restaurant = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activity_logs',
    )
    target_id = models.PositiveIntegerField(null=True, blank=True)
    target_type = models.CharField(max_length=100, blank=True, default='')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Registo de atividade'
        verbose_name_plural = 'Registos de atividade'
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['activity_type', 'created_at']),
            models.Index(fields=['restaurant', 'created_at']),
        ]

    def __str__(self):
        user_str = self.user.name if self.user else 'Anónimo'
        return f"[{self.activity_type}] {user_str} — {self.description[:60]}"

    @staticmethod
    def log(activity_type, description, user=None, restaurant=None,
            target_id=None, target_type='', ip_address=None, user_agent=''):
        """
        Convenience method to create an activity log entry.
        """
        ActivityLog.objects.create(
            activity_type=activity_type,
            description=description,
            user=user,
            restaurant=restaurant,
            target_id=target_id,
            target_type=target_type,
            ip_address=ip_address,
            user_agent=user_agent,
        )
