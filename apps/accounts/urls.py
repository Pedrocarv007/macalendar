from django.urls import path
from .views import LoginView, LogoutView, MeView, ProfileView

urlpatterns = [
    path('login', LoginView.as_view(), name='api-login'),
    path('logout', LogoutView.as_view(), name='api-logout'),
    path('me', MeView.as_view(), name='api-me'),
    path('profile', ProfileView.as_view(), name='api-profile'),
]
