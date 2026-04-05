from rest_framework import serializers
from django.contrib.gis.geos import Point
from .models import DeliveryAgent, Delivery


class DeliveryAgentSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    current_location = serializers.SerializerMethodField()

    class Meta:
        model = DeliveryAgent
        fields = [
            'id', 'full_name', 'assigned_zone', 'vehicle_type',
            'status', 'rating_avg', 'total_deliveries',
            'current_location', 'last_location_update', 'is_active'
        ]
        read_only_fields = fields

    def get_current_location(self, obj):
        """Return GeoJSON representation of the PointField"""
        if obj.current_location:
            return {
                "type": "Point",
                "coordinates": [obj.current_location.x, obj.current_location.y]
            }
        return None


class DeliverySerializer(serializers.ModelSerializer):
    order_id = serializers.IntegerField(source='order.id', read_only=True)
    agent_name = serializers.CharField(source='agent.full_name', read_only=True, default=None)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Delivery
        fields = [
            'id', 'order_id', 'agent', 'agent_name', 'status', 'status_display',
            'pickup_time', 'actual_delivery_time', 'delivery_fee',
            'customer_rating', 'customer_comment', 'delivery_photo',
            'created_at', 'updated_at'
        ]
        read_only_fields = fields