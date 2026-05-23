from django.db import models


class Restaurant(models.Model):
    # Link para o restaurante no SSO (sem FK cross-DB — só o ID numérico)
    sso_id  = models.IntegerField(unique=True, null=True, blank=True, default=None)
    name    = models.CharField(max_length=100)
    code    = models.CharField(max_length=10, unique=True, null=True, blank=True, default=None)
    address = models.CharField(max_length=200, blank=True, default='')
    phone = models.CharField(max_length=30, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    capacity = models.PositiveIntegerField(null=True, blank=True)
    opening_hours = models.CharField(max_length=100, blank=True, default='')
    description = models.TextField(blank=True, default='')
    photo_filename = models.CharField(max_length=255, blank=True, default='')
    manager = models.ForeignKey(
        'accounts.Employee',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='managed_restaurants',
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def photo_url(self):
        if self.photo_filename:
            return f"/media/photos/restaurants/{self.photo_filename}"
        return "/static/img/default-restaurant.png"
