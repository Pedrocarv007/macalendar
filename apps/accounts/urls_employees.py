from django.urls import path
from .views_employees import EmployeeListCreateView, EmployeeDetailView, EmployeePhotoView

urlpatterns = [
    path('', EmployeeListCreateView.as_view(), name='employee-list'),
    path('<int:pk>', EmployeeDetailView.as_view(), name='employee-detail'),
    path('<int:pk>/photo', EmployeePhotoView.as_view(), name='employee-photo'),
]
