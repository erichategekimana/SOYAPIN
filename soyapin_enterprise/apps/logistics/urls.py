from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AgentViewSet, DeliveryViewSet

router = DefaultRouter()
router.register(r'agents', AgentViewSet, basename='agent')
router.register(r'deliveries', DeliveryViewSet, basename='delivery')

urlpatterns = [
    path('', include(router.urls)),
]