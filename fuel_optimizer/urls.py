from django.urls import path
from .views import DashboardView

app_name = 'fuel_optimizer'

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
]
