from rest_framework import serializers
from .models import Category, Vendor, Product, Inventory


class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(source='products.count', read_only=True)
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'product_count', 'created_at']


class InventorySerializer(serializers.ModelSerializer):
    needs_restock = serializers.BooleanField(read_only=True)
    status = serializers.SerializerMethodField()
    
    class Meta:
        model = Inventory
        fields = [
            'quantity_available', 
            'restock_threshold', 
            'expiry_date', 
            'batch_number',
            'needs_restock',
            'status'
        ]
    
    def get_status(self, obj):
        if obj.quantity_available == 0:
            return 'out_of_stock'
        elif obj.needs_restock:
            return 'low_stock'
        return 'in_stock'


class ProductListSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source='vendor.business_name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    stock_status = serializers.SerializerMethodField()
    protein_content = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'base_price', 'image_url',
            'vendor_name', 'category_name',
            'stock_status', 'protein_content',
            'is_published', 'created_at'
        ]
    
    def get_stock_status(self, obj):
        if not obj.is_in_stock:
            return 'unavailable'
        if obj.inventory.needs_restock:
            return 'limited'
        return 'available'


class ProductDetailSerializer(serializers.ModelSerializer):
    vendor = serializers.StringRelatedField()
    category = CategorySerializer(read_only=True)
    inventory = InventorySerializer(read_only=True)
    nutritional_data = serializers.JSONField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'base_price', 'current_price',
            'image_url', 'nutritional_data',
            'vendor', 'category', 'inventory',
            'is_published', 'is_deleted',
            'created_at', 'updated_at'
        ]


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category',
        required=False,
        allow_null=True
    )
    initial_stock = serializers.IntegerField(
        write_only=True,
        required=False,
        min_value=0,
        default=0
    )
    
    class Meta:
        model = Product
        fields = [
            'name', 'description', 'base_price', 'image_url',
            'category_id', 'nutritional_data', 'is_published',
            'initial_stock'
        ]
    
    def create(self, validated_data):
        initial_stock = validated_data.pop('initial_stock', 0)
        validated_data['vendor'] = self.context['request'].user.vendor_profile
        
        product = super().create(validated_data)
        
        Inventory.objects.create(
            product=product,
            quantity_available=initial_stock
        )
        
        return product


class VendorSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    product_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Vendor
        fields = [
            'id', 'business_name', 'user_email',
            'tin_number', 'location_data', 'verification_status',
            'bio', 'product_count', 'created_at'
        ]