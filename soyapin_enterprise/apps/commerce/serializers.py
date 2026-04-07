from rest_framework import serializers
from .models import Cart, CartItem, Order, OrderItem, Payment
from apps.catalog.models import Product
from apps.catalog.serializers import ProductListSerializer


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source='product',
        write_only=True
    )
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    
    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_id', 'quantity', 'unit_price', 'subtotal']
        read_only_fields = ['unit_price']


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    item_count = serializers.IntegerField(read_only=True)
    total_protein = serializers.SerializerMethodField()
    total_calories = serializers.SerializerMethodField()
    protein_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = Cart
        fields = [
            'id', 'items', 'total', 'item_count',
            'created_at', 'updated_at',
            'total_protein', 'total_calories', 'protein_percentage'
            ]
    def get_total_protein(self, obj):
        return obj.get_total_protein()
    def get_total_calories(self, obj):
        return obj.get_total_calories()
    def get_protein_percentage(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.get_protein_percentage(request.user)
        return None


class AddToCartSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, default=1)


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'quantity', 'unit_price', 'subtotal']


class OrderListSerializer(serializers.ModelSerializer):
    item_count = serializers.IntegerField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Order
        fields = ['id', 'status', 'status_display', 'total_amount', 'item_count', 'created_at']


class OrderDetailSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Order
        fields = ['id', 'status', 'status_display', 'total_amount', 'items', 'notes', 'created_at']


class CreateOrderSerializer(serializers.Serializer):
    shipping_address_id = serializers.IntegerField(required=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class PaymentSerializer(serializers.ModelSerializer):
    provider_display = serializers.CharField(source='get_provider_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Payment
        fields = ['id', 'provider', 'provider_display', 'transaction_ref', 'amount', 'status', 'status_display', 'completed_at']


class CreatePaymentSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=Payment.Provider.choices)
    phone_number = serializers.CharField(required=False)