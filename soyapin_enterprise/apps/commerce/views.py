from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
import uuid
from .services import PaymentService

from .models import Cart, CartItem, Order, Payment
from .serializers import (
    CartSerializer, CartItemSerializer, AddToCartSerializer,
    OrderListSerializer, OrderDetailSerializer, CreateOrderSerializer,
    PaymentSerializer, CreatePaymentSerializer
)
from apps.catalog.models import Product
from apps.identity.models import UserAddress


class CartViewSet(viewsets.ViewSet):
    """
    Shopping cart operations
    GET /commerce/cart/ - view my cart
    POST /commerce/cart/add/ - add item
    POST /commerce/cart/remove/ - remove item
    DELETE /commerce/cart/clear/ - empty cart
    """
    permission_classes = [IsAuthenticated]
    
    def get_cart(self):
        """Get or create cart for current user"""
        cart, created = Cart.objects.get_or_create(user=self.request.user)
        return cart
    
    def list(self, request):
        """GET /cart/ - view cart"""
        cart = self.get_cart()
        serializer = CartSerializer(cart, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def add(self, request):
        """POST /cart/add/ - add product to cart"""
        serializer = AddToCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        product = get_object_or_404(Product, id=serializer.validated_data['product_id'])
        quantity = serializer.validated_data.get('quantity', 1)
        
        cart = self.get_cart()
        
        try:
            cart_item = cart.add_item(product, quantity)
            return Response({
                'status': 'added',
                'cart_item': CartItemSerializer(cart_item).data,
                'cart_total': cart.total
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'])
    def remove(self, request):
        """POST /cart/remove/ - remove item from cart"""
        item_id = request.data.get('item_id')
        if not item_id:
            return Response(
                {'error': 'item_id required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cart = self.get_cart()
        try:
            item = cart.items.get(id=item_id)
            item.delete()
            return Response({
                'status': 'removed',
                'cart_total': cart.total
            })
        except CartItem.DoesNotExist:
            return Response(
                {'error': 'Item not found in cart'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['delete'])
    def clear(self, request):
        """DELETE /cart/clear/ - empty cart"""
        cart = self.get_cart()
        cart.clear()
        return Response({'status': 'cart cleared'})


class OrderViewSet(viewsets.ViewSet):
    """
    Order management
    GET /commerce/orders/ - my orders
    POST /commerce/orders/checkout/ - cart → order
    GET /commerce/orders/{id}/ - order details
    POST /commerce/orders/{id}/cancel/ - cancel order
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Users see their own orders, admins see all"""
        user = self.request.user
        if getattr(user, 'role', None) == 'admin':
            return Order.objects.all()
        return Order.objects.filter(user=user)
    
    def list(self, request):
        """GET /orders/ - list my orders"""
        orders = self.get_queryset()
        serializer = OrderListSerializer(orders, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, pk=None):
        """GET /orders/{id}/ - order details"""
        order = get_object_or_404(self.get_queryset(), pk=pk)
        serializer = OrderDetailSerializer(order)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def checkout(self, request):
        """
        POST /orders/checkout/
        Convert cart to order
        {
            "shipping_address_id": 1,
            "notes": "Leave at door"
        }
        """
        serializer = CreateOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get user's cart
        try:
            cart = request.user.cart
        except Cart.DoesNotExist:
            return Response(
                {'error': 'Cart is empty'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not cart.items.exists():
            return Response(
                {'error': 'Cart is empty'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get shipping address
        address_id = serializer.validated_data['shipping_address_id']
        try:
            shipping_address = request.user.addresses.get(id=address_id)
        except UserAddress.DoesNotExist:
            return Response(
                {'error': 'Invalid shipping address'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        
        # Validate scheduled datetime
        delivery_option = serializer.validated_data.get('delivery_option')
        scheduled_datetime = serializer.validated_data.get('scheduled_datetime')
        if delivery_option == Order.DeliveryOption.SCHEDULED and not scheduled_datetime:
            return Response(
                {"error": "scheduled_datetime is required for scheduled delivery"},
                status=status.HTTP_400_BAD_REQUEST
            )
        if delivery_option == Order.DeliveryOption.EXPRESS:
            scheduled_datetime = None  # ensure null for express

        try:
            with transaction.atomic():
                order = cart.to_order(shipping_address)
                order.notes = serializer.validated_data.get('notes', '')
                order.delivery_option = delivery_option
                order.scheduled_datetime = scheduled_datetime
                order.save()

                return Response({
                    'status': 'order created',
                    'order_id': order.id,
                    'total': order.total_amount,
                    'delivery_option': order.delivery_option,
                    'scheduled_datetime': order.scheduled_datetime,
                    'payment_url': f'/api/v1/commerce/orders/{order.id}/pay/'
                }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """POST /orders/{id}/cancel/ - cancel pending order"""
        order = get_object_or_404(self.get_queryset(), pk=pk)
        
        if order.status != Order.Status.PENDING:
            return Response(
                {'error': f'Cannot cancel order with status {order.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            order.status = Order.Status.CANCELLED
            order.save()
            # Restore stock
            for item in order.items.all():
                item.product.inventory.restock(item.quantity)
            
            return Response({'status': 'order cancelled', 'refund': 'stock restored'})
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get', 'post'])
    def pay(self, request, pk=None):
        """
        GET /orders/{id}/pay/ - payment status
        POST /orders/{id}/pay/ - initiate payment
        """
        order = get_object_or_404(self.get_queryset(), pk=pk)
        
        if request.method == 'GET':
            try:
                payment = order.payment
                serializer = PaymentSerializer(payment)
                return Response(serializer.data)
            except Payment.DoesNotExist:
                return Response(
                    {'status': 'no payment initiated'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # POST - initiate payment
        if order.status != Order.Status.PENDING:
            return Response(
                {'error': 'Order already paid or cancelled'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = CreatePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Generate transaction reference
        import uuid
        transaction_ref = f"SOYA{uuid.uuid4().hex[:12].upper()}"
        
        payment = Payment.objects.create(
            order=order,
            provider=serializer.validated_data['provider'],
            transaction_ref=transaction_ref,
            amount=order.total_amount
        )
        
        return Response({
            'status': 'payment initiated',
            'transaction_ref': transaction_ref,
            'amount': payment.amount,
            'provider': payment.get_provider_display(),
            'instructions': f'Complete payment via {payment.get_provider_display()}'
        })
    
    @action(detail=True, methods=['post'])
    def confirm_payment(self, request, pk=None):
        """POST /orders/{id}/confirm_payment/ - confirm payment received"""
        order = get_object_or_404(self.get_queryset(), pk=pk)
        transaction_ref = request.data.get('transaction_ref')
        
        if not transaction_ref:
            return Response(
                {'error': 'transaction_ref required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            payment = order.payment
            if payment.transaction_ref != transaction_ref:
                return Response(
                    {'error': 'Invalid transaction reference'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            payment.confirm()
            return Response({
                'status': 'payment confirmed',
                'order_status': order.status
            })
        except Payment.DoesNotExist:
            return Response(
                {'error': 'No payment found for this order'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        
    

   

    @action(detail=True, methods=['post'], url_path='mtn-pay')
    def mtn_pay(self, request, pk=None):
        order = get_object_or_404(self.get_queryset(), pk=pk)

        # Check if order already has a completed payment
        if hasattr(order, 'payment') and order.payment.status == Payment.Status.COMPLETED:
            return Response(
                {"error": "Order already paid"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if order.status != Order.Status.PENDING:
            return Response(
                {"error": "Order cannot be paid (status is not PENDING)"},
                status=status.HTTP_400_BAD_REQUEST
            )

        phone_number = request.data.get('phone_number')
        if not phone_number:
            return Response(
                {"error": "phone_number is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Delete any existing failed/pending payment to avoid conflict
        if hasattr(order, 'payment'):
            order.payment.delete()

        from .services import PaymentService
        success, txn_ref, message = PaymentService.initiate_mtn_payment(order, phone_number)

        if success:
            payment = Payment.objects.create(
                order=order,
                provider=Payment.Provider.MTN,
                transaction_ref=txn_ref,
                amount=order.total_amount,
                status=Payment.Status.COMPLETED,
                completed_at=timezone.now()
            )
            order.status = Order.Status.PAID
            order.save()
            return Response({
                "status": "payment_success",
                "transaction_ref": txn_ref,
                "amount": payment.amount,
                "provider": "MTN Mobile Money",
                "message": message
            })
        else:
            Payment.objects.create(
                order=order,
                provider=Payment.Provider.MTN,
                transaction_ref=f"FAILED-{uuid.uuid4().hex[:8]}",
                amount=order.total_amount,
                status=Payment.Status.FAILED,
                failure_reason=message
            )
            return Response(
                {"error": message, "status": "payment_failed"},
                status=status.HTTP_400_BAD_REQUEST
            )