from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/identity/', include('apps.identity.urls')),
    path('api/v1/catalog/', include('apps.catalog.urls')), 
    path('api/v1/commerce/', include('apps.commerce.urls')),
    path('api/v1/logistics/', include('apps.logistics.urls')),
    path('api/v1/health/', include('apps.health.urls')),
]