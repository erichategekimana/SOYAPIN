from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Category, Vendor, Product
from .serializers import (
    CategorySerializer, 
    VendorSerializer,
    ProductListSerializer, 
    ProductDetailSerializer,
    ProductCreateUpdateSerializer
)


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = 'slug'
    
    @action(detail=True, methods=['get'])
    def products(self, request, slug=None):
        category = self.get_object()
        products = Product.objects.filter(
            category=category,
            is_published=True,
            is_deleted=False
        )
        serializer = ProductListSerializer(products, many=True)
        return Response(serializer.data)


class VendorViewSet(viewsets.ModelViewSet):
    queryset = Vendor.objects.all()
    serializer_class = VendorSerializer


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ProductListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ProductCreateUpdateSerializer
        return ProductDetailSerializer
    
    @action(detail=False, methods=['get'])
    def in_stock(self, request):
        products = self.get_queryset().filter(inventory__quantity_available__gt=0)
        serializer = ProductListSerializer(products, many=True)
        return Response(serializer.data)