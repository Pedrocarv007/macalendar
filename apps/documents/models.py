from django.db import models


class Document(models.Model):
    DOCUMENT_TYPES = [
        ('birthday', 'Aniversário'),
        ('praise', 'Elogio'),
        ('certificate', 'Certificado'),
        ('memo', 'Memorando'),
        ('photo', 'Foto'),
        ('welcome', 'Boas-Vindas'),
        ('employee_month', 'Funcionário do Mês'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Rascunho'),
        ('generated', 'Gerado'),
        ('sent', 'Enviado'),
        ('uploaded', 'Carregado'),
    ]

    title = models.CharField(max_length=200)
    document_type = models.CharField(max_length=30, choices=DOCUMENT_TYPES, db_index=True)
    template_name = models.CharField(max_length=100, blank=True, default='')

    employee = models.ForeignKey(
        'accounts.Employee',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='documents',
    )
    worker = models.ForeignKey(
        'workers.Worker',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='documents',
        db_constraint=False,
    )
    restaurant = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.CASCADE,
        related_name='documents',
    )
    created_by = models.ForeignKey(
        'accounts.Employee',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_documents',
    )

    content = models.TextField(blank=True, default='')
    filename = models.CharField(max_length=255, blank=True, default='')
    file_path = models.CharField(max_length=500, blank=True, default='')
    file_size = models.PositiveIntegerField(null=True, blank=True)
    file_extension = models.CharField(max_length=10, blank=True, default='')
    description = models.TextField(blank=True, default='')
    tags = models.CharField(max_length=500, blank=True, default='')
    is_public = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
