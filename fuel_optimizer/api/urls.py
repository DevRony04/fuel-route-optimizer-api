from django.urls import path
from .views import RouteOptimizerView

urlpatterns = [
    path('optimize-route/', RouteOptimizerView.as_view(), name='optimize-route'),
]
