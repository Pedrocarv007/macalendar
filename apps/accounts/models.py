"""
Accounts models: Employee (custom user) and UserSettings.
"""
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from django.conf import settings
import datetime


class EmployeeManager(BaseUserManager):
    """Custom manager for the Employee user model."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('O endereço de email é obrigatório.')
        email = self.normalize_email(email)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', 'employee')
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('role', 'admin')
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('O administrador principal tem de pertencer à equipa.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('O administrador principal tem de ter privilégios totais.')

        return self.create_user(email, password, **extra_fields)

    def active(self):
        return self.get_queryset().filter(is_active=True)

    def by_restaurant(self, restaurant_id):
        return self.active().filter(restaurant_id=restaurant_id)


class Employee(AbstractBaseUser, PermissionsMixin):
    """
    Modelo de utilizador do MC.
    Uses email for authentication instead of username.
    """

    ROLE_CHOICES = [
        ('admin', 'Administrador'),
        ('rh', 'RH'),
        ('marketing', 'Marketing'),
        ('administrativa', 'Administrativa'),
        ('manager', 'Gerente'),
        ('sub_manager', 'Sub-Gerente'),
        ('shift_manager', 'Gerente de Turno'),
        ('treinador', 'Treinador'),
        ('coucher', 'Coucher'),
        ('rp', 'Relações Públicas'),
        ('employee', 'Colaborador'),
    ]

    EMPLOYEE_TYPE_CHOICES = [
        ('treinador', 'Treinador'),
        ('relacoes_publicas', 'Relações Públicas'),
        ('colaborador', 'Colaborador'),
    ]

    # Core identification
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=30, blank=True, default='')

    # Role and type
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default='employee')
    employee_type = models.CharField(
        max_length=30,
        choices=EMPLOYEE_TYPE_CHOICES,
        blank=True,
        default='',
        help_text='Only applicable when role is "employee".',
    )

    # Work info
    position = models.CharField(max_length=100, blank=True, default='')
    department = models.CharField(max_length=100, blank=True, default='')
    hire_date = models.DateField(null=True, blank=True)
    birth_date = models.DateField(null=True, blank=True)

    # Restaurant assignment
    restaurant = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employees',
    )

    # Profile
    photo_filename = models.CharField(max_length=255, blank=True, default='')
    address = models.TextField(blank=True, default='')
    notes = models.TextField(blank=True, default='')

    # Django auth fields
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = EmployeeManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    class Meta:
        verbose_name = 'Utilizador'
        verbose_name_plural = 'Utilizadores'
        ordering = ['name']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
            models.Index(fields=['restaurant']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_role_display()})"

    @property
    def age(self):
        if not self.birth_date:
            return None
        today = datetime.date.today()
        delta = today - self.birth_date
        years = delta.days // 365
        return years

    @property
    def next_birthday(self):
        if not self.birth_date:
            return None
        today = datetime.date.today()
        this_year = today.replace(month=self.birth_date.month, day=self.birth_date.day)
        if this_year < today:
            return this_year.replace(year=today.year + 1)
        return this_year

    @property
    def days_until_birthday(self):
        nb = self.next_birthday
        if nb is None:
            return None
        return (nb - datetime.date.today()).days

    @property
    def is_birthday_today(self):
        if not self.birth_date:
            return False
        today = datetime.date.today()
        return self.birth_date.month == today.month and self.birth_date.day == today.day

    @property
    def work_years(self):
        if not self.hire_date:
            return None
        delta = datetime.date.today() - self.hire_date
        return round(delta.days / 365, 1)

    @property
    def photo_url(self):
        # 1. Avatar do SSO — fonte de verdade; tem prioridade máxima
        # Import local para evitar import circular accounts → workers → accounts
        from apps.workers.utils import sso_avatar_url_for_email
        sso_url = sso_avatar_url_for_email(self.email)
        if sso_url:
            return sso_url
        # 2. Carregamento local no MC — alternativa quando não há avatar SSO
        if self.photo_filename:
            return f"/media/photos/employees/{self.photo_filename}"
        # 3. Sem foto — usa o avatar genérico
        return "/static/img/default-avatar.svg"

    def is_super_role(self):
        return self.role in settings.SUPER_ROLES

    def can_manage_employees(self):
        from .permissions import can_manage_employees
        return can_manage_employees(self)

    def can_manage_restaurant(self):
        from .permissions import can_manage_restaurant
        return can_manage_restaurant(self)

    def can_create_posts(self):
        return True  # all authenticated users can create posts


class UserSettings(models.Model):
    """
    Per-user preference and security settings.
    """
    user = models.OneToOneField(
        Employee,
        on_delete=models.CASCADE,
        related_name='settings',
    )
    timezone = models.CharField(max_length=60, default='Europe/Lisbon')
    notifications_enabled = models.BooleanField(default=True)
    email_notifications = models.BooleanField(default=True)
    two_factor_enabled = models.BooleanField(default=False)
    auto_logout_enabled = models.BooleanField(default=True)
    session_timeout_minutes = models.PositiveIntegerField(default=480)  # 8 hours
    items_per_page = models.PositiveIntegerField(default=20)
    dark_mode = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Preferências do utilizador'
        verbose_name_plural = 'Preferências dos utilizadores'

    def __str__(self):
        return f"Preferências de {self.user.name}"
