from rest_framework import serializers
from .models import HealthProfile

class HealthProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthProfile
        fields = [
            'id', 'dietary_goal', 'daily_protein_goal_g', 'allergies',
            'activity_level', 'age', 'weight_kg', 'height_cm', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']