from django.urls import path
from .views import HealthProfileDetailView

urlpatterns = [
    path('profile/', HealthProfileDetailView.as_view(), name='health-profile'),
]