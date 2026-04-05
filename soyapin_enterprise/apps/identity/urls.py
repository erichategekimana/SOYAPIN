from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, AddressViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'addresses', AddressViewSet, basename='address')


urlpatterns = router.urls