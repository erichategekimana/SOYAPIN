from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import HealthProfile
from .serializers import HealthProfileSerializer

class HealthProfileDetailView(generics.RetrieveUpdateAPIView):
    """
    GET /api/v1/health/profile/ - retrieve current user's health profile
    PUT /api/v1/health/profile/ - update profile (creates if not exists)
    """
    serializer_class = HealthProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        profile, created = HealthProfile.objects.get_or_create(user=self.request.user)
        return profile