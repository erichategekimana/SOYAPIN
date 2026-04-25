from django.shortcuts import render
from drf_spectacular.utils import extend_schema

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from .services import recommend_products
from .serializers import RecommendationResponseSerializer
from apps.health.serializers import HealthProfileSerializer
from apps.catalog.serializers import ProductListSerializer

class RecommendationView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = RecommendationResponseSerializer

    @extend_schema(
        responses=RecommendationResponseSerializer,
        description="Get personalized product recommendations based on user's health profile and purchase history."
    )

    def get(self, request):
        user = request.user
        products = recommend_products(user, limit=10)
        profile_serializer = HealthProfileSerializer(user.health_profile) if hasattr(user, 'health_profile') else None

        return Response({
            "recommended_products": ProductListSerializer(products, many=True, context={'request': request}).data,
            "user_health_profile": profile_serializer.data if profile_serializer else None
        })