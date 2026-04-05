from rest_framework import serializers
from .models import User, UserAddress

class UserAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAddress
        fields = ['id', 'address_line', 'city', 'coordinates', 'is_default']

class UserSerializer(serializers.ModelSerializer):
    addresses = UserAddressSerializer(many=True, read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 
            'phone_number', 'role', 'is_active', 
            'created_at', 'addresses'
        ]
        read_only_fields = ['created_at', 'id']