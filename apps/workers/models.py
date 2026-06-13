import datetime
from django.db import models


class SSOManager(models.Manager):
    """Manager que força todas as queries para a base de dados 'sso'."""
    def get_queryset(self):
        return super().get_queryset().using('sso')


class SSOUser(models.Model):
    """
    Leitura do SSO — tabela Usuários.
    Fonte de verdade para funcionários com acesso ao Mac Calendar.
    Mac Calendar não escreve nesta tabela.
    """
    username       = models.CharField(max_length=150)
    first_name     = models.CharField(max_length=150, blank=True)
    last_name      = models.CharField(max_length=150, blank=True)
    email          = models.EmailField()
    role           = models.CharField(max_length=30, blank=True)
    is_active      = models.BooleanField(default=True)
    is_staff       = models.BooleanField(default=False)
    phone          = models.CharField(max_length=30, blank=True)
    department     = models.CharField(max_length=100, blank=True)
    job_title      = models.CharField(max_length=100, blank=True)
    birth_date     = models.DateField(null=True, blank=True)
    hire_date      = models.DateField(null=True, blank=True)
    address        = models.TextField(blank=True)
    notes          = models.TextField(blank=True)
    avatar         = models.CharField(max_length=255, blank=True)
    restaurant_id  = models.IntegerField(null=True, blank=True)
    date_joined    = models.DateTimeField()
    created_at     = models.DateTimeField()
    updated_at     = models.DateTimeField()

    objects = SSOManager()

    class Meta:
        db_table = 'Usuários'
        managed  = False
        ordering = ['first_name', 'last_name']

    def __str__(self):
        return f'{self.first_name} {self.last_name} <{self.email}>'

    @property
    def name(self):
        full = f'{self.first_name} {self.last_name}'.strip()
        return full or self.username or self.email


class SSORestaurant(models.Model):
    """
    Leitura do SSO — tabela Restaurants.
    Usado para resolver nomes/códigos de restaurante nos workers.
    """
    name      = models.CharField(max_length=100)
    code      = models.CharField(max_length=10)
    city      = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)

    objects = SSOManager()

    class Meta:
        db_table = 'Restaurants'
        managed  = False
        ordering = ['name']

    def __str__(self):
        return f'{self.code} — {self.name}'


class Worker(models.Model):
    """
    Leitura do SSO — tabela Usuários (colaboradores/crew).
    Mac Calendar não escreve nesta tabela; toda a gestão é feita no SSO Portal.
    """
    first_name      = models.CharField(max_length=100)
    last_name       = models.CharField(max_length=100)
    employee_number = models.CharField(max_length=20, blank=True)
    email           = models.EmailField(blank=True)
    phone           = models.CharField(max_length=20, blank=True)
    birth_date      = models.DateField(null=True, blank=True)
    hire_date       = models.DateField(null=True, blank=True)
    address         = models.TextField(blank=True)
    photo_filename  = models.CharField(max_length=255, blank=True)
    avatar          = models.CharField(max_length=255, blank=True)
    notes           = models.TextField(blank=True)
    job_role        = models.CharField(max_length=100, blank=True)
    role            = models.CharField(max_length=30, blank=True)
    restaurant_id   = models.IntegerField(null=True, blank=True)
    training_status = models.CharField(max_length=20, blank=True)
    is_active       = models.BooleanField(default=True)
    created_at      = models.DateTimeField()
    updated_at      = models.DateTimeField()

    objects = SSOManager()

    class Meta:
        db_table = 'Usuários'
        managed  = False
        ordering = ['first_name', 'last_name']

    def __str__(self):
        return f'{self.first_name} {self.last_name}'

    @property
    def name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    @property
    def age(self):
        if not self.birth_date:
            return None
        return (datetime.date.today() - self.birth_date).days // 365

    @property
    def next_birthday(self):
        if not self.birth_date:
            return None
        today = datetime.date.today()
        bd = today.replace(month=self.birth_date.month, day=self.birth_date.day)
        if bd < today:
            bd = bd.replace(year=today.year + 1)
        return bd

    @property
    def days_until_birthday(self):
        nb = self.next_birthday
        return (nb - datetime.date.today()).days if nb else None

    @property
    def photo_url(self):
        if self.photo_filename:
            return f'/media/photos/workers/{self.photo_filename}'
        if self.avatar:
            # Avatar já é URL completo (ex: Google) → usar como está;
            # caso contrário é caminho relativo no SSO → servir por /sso-media/.
            if self.avatar.lower().startswith(('http://', 'https://')):
                return self.avatar
            from django.conf import settings
            base = settings.SSO_MEDIA_BASE_URL.rstrip('/')
            return f"{base}/{self.avatar.lstrip('/')}"
        return '/static/img/default-avatar.svg'
