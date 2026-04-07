from rest_framework import serializers
from apps.catalog.serializers import ProductListSerializer

class RecommendationResponseSerializer(serializers.Serializer):
    recommended_products = ProductListSerializer(many=True)
    user_health_profile = serializers.DictField()