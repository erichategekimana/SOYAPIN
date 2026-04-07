from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework import status
from apps.commerce.models import Order
from django.contrib.gis.db.models.functions import Distance
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import DeliveryAgent, Delivery
from .serializers import DeliveryAgentSerializer, DeliverySerializer
from apps.identity.permissions import IsAdminUser, IsAgentUser  # we'll define these


class IsAgentOrReadOnly(permissions.BasePermission):
    """Agents can read their own profile and deliveries; others read-only if admin/customer"""
    def has_object_permission(self, request, view, obj):
        # SAFE_METHODS = GET, HEAD, OPTIONS
        if request.method in permissions.SAFE_METHODS:
            if isinstance(obj, DeliveryAgent):
                return request.user == obj.user or request.user.is_staff
            elif isinstance(obj, Delivery):
                # Customer can see delivery for their own order
                if request.user == obj.order.user:
                    return True
                # Agent can see their own deliveries
                if obj.agent and request.user == obj.agent.user:
                    return True
                # Admin/staff can see all
                return request.user.is_staff
        return False


class AgentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List and retrieve delivery agents.
    - Admin: all agents
    - Agent: only their own profile
    - Customer: none (except maybe public list? We restrict to empty)
    """
    serializer_class = DeliveryAgentSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return DeliveryAgent.objects.all()
        if hasattr(user, 'agent_profile'):
            return DeliveryAgent.objects.filter(user=user)
        return DeliveryAgent.objects.none()
    

    @action(detail=True, methods=['post'], url_path='update-location')
    def update_location(self, request, pk=None):
        """
        POST /agents/{id}/update-location/
        Body: {"lat": -1.9441, "lng": 30.0619}
        """
        agent = self.get_object()
        # Ensure the authenticated user owns this agent profile
        if request.user != agent.user and not request.user.is_staff:
            return Response(
                {"error": "You can only update your own location"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        lat = request.data.get('lat')
        lng = request.data.get('lng')
        if lat is None or lng is None:
            return Response(
                {"error": "Both 'lat' and 'lng' are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            lat = float(lat)
            lng = float(lng)
        except ValueError:
            return Response(
                {"error": "lat and lng must be numbers"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        agent.update_location(lat, lng)
        return Response({
            "status": "location updated",
            "current_location": {
                "type": "Point",
                "coordinates": [lng, lat]
            },
            "last_update": agent.last_location_update
        })

    @action(detail=True, methods=['get'], url_path='nearby-orders')
    def nearby_orders(self, request, pk=None):
        """
        GET /agents/{id}/nearby-orders/?radius=5 (km, default=5)
        Returns pending deliveries (orders with status='paid' but no delivery or delivery not yet assigned)
        within a radius (km) from the agent's current location.
        """
        agent = self.get_object()
        if not agent.current_location:
            return Response(
                {"error": "Agent location not set. Please update location first."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        radius_km = float(request.query_params.get('radius', 5))
        radius_m = radius_km * 1000
        
        # Get orders that are PAID and do NOT have a delivery assigned (or delivery status = PREPARING)
        # We need to find deliveries that are either:
        # - no delivery exists for the order
        # - delivery exists but agent is null (unassigned) or status is PREPARING
        # But easier: filter orders where delivery is None OR delivery.agent is None
        # However, Delivery has OneToOneField, so order.delivery exists if created.
        
        # Using the signal, deliveries are created when order is PAID.
        # So we want deliveries that are not yet assigned (agent is null) and status not CANCELLED.
        
        deliveries = Delivery.objects.filter(
            agent__isnull=True,
            status__in=[Delivery.Status.PREPARING, Delivery.Status.READY_FOR_PICKUP],
            order__status=Order.Status.PAID  # ensure order is paid
        ).select_related('order', 'order__shipping_address')
        
        # Annotate with distance from agent's location to order's shipping address coordinates
        # Note: order.shipping_address has coordinates (PointField)
        deliveries = deliveries.annotate(
            distance=Distance('order__shipping_address__coordinates', agent.current_location)
        ).filter(
            distance__lte=radius_m,
            order__shipping_address__coordinates__isnull=False
        ).order_by('distance')
        
        serializer = DeliverySerializer(deliveries, many=True)
        return Response({
            "count": deliveries.count(),
            "radius_km": radius_km,
            "results": serializer.data
        })
    


    @action(detail=True, methods=['post'], url_path='set-status')
    def set_status(self, request, pk=None):
        """
        POST /agents/{id}/set-status/
        Body: {"status": "available" | "busy" | "offline"}
        """
        agent = self.get_object()
        if request.user != agent.user and not request.user.is_staff:
            return Response(
                {"error": "You can only update your own status"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        new_status = request.data.get('status')
        if new_status not in [DeliveryAgent.Status.AVAILABLE, DeliveryAgent.Status.BUSY, DeliveryAgent.Status.OFFLINE]:
            return Response(
                {"error": f"Invalid status. Choose from {DeliveryAgent.Status.values}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        agent.status = new_status
        agent.save()
        return Response({
            "status": agent.status,
            "message": f"Status updated to {agent.get_status_display()}"
        })
    

    @action(detail=True, methods=['get'], url_path='ratings')
    def ratings(self, request, pk=None):
        """
        GET /agents/{id}/ratings/
        Returns list of ratings given to this agent (from completed deliveries).
        """
        agent = self.get_object()
        # Allow agent to see own ratings, admin sees all, others forbidden
        if request.user != agent.user and not request.user.is_staff:
            return Response(
                {"error": "Permission denied"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        deliveries = Delivery.objects.filter(
            agent=agent,
            customer_rating__isnull=False
        ).select_related('order').order_by('-created_at')
        
        data = [
            {
                "delivery_id": d.id,
                "order_id": d.order.id,
                "rating": d.customer_rating,
                "comment": d.customer_comment,
                "created_at": d.created_at,
            }
            for d in deliveries
        ]
        return Response({
            "agent": agent.full_name,
            "average_rating": agent.rating_avg,
            "total_ratings": deliveries.count(),
            "ratings": data
        })
    

    @action(detail=True, methods=['get'], url_path='payouts')
    def payouts(self, request, pk=None):
        """
        GET /agents/{id}/payouts/
        Returns list of payouts for the agent.
        """
        agent = self.get_object()
        if request.user != agent.user and not request.user.is_staff:
            return Response(
                {"error": "Permission denied"},
                status=status.HTTP_403_FORBIDDEN
            )

        payouts = agent.payouts.all().order_by('-created_at')
        data = [
            {
                "id": p.id,
                "amount": p.amount,
                "status": p.status,
                "description": p.description,
                "created_at": p.created_at,
                "processed_at": p.processed_at,
                "transaction_reference": p.transaction_reference,
            }
            for p in payouts
        ]
        return Response({
            "agent": agent.full_name,
            "total_payouts": payouts.count(),
            "pending_amount": sum(p.amount for p in payouts if p.status == 'pending'),
            "payouts": data
        })
    








class DeliveryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List and retrieve deliveries.
    - Admin: all deliveries
    - Agent: deliveries assigned to them
    - Customer: deliveries for orders they placed
    """
    serializer_class = DeliverySerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Delivery.objects.all()
        if hasattr(user, 'agent_profile'):
            return Delivery.objects.filter(agent=user.agent_profile)
        # Customer: deliveries of their orders
        return Delivery.objects.filter(order__user=user)
    



    @action(detail=True, methods=['post'], url_path='pickup')
    def pickup(self, request, pk=None):
        """
        POST /deliveries/{id}/pickup/
        Agent marks that they have picked up the order.
        Transition: preparing → picked_up
        """
        delivery = self.get_object()
        agent = delivery.agent
        
        # Only the assigned agent can update
        if not agent or (request.user != agent.user and not request.user.is_staff):
            return Response(
                {"error": "You are not assigned to this delivery"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            delivery.transition_status(Delivery.Status.PICKED_UP)
            return Response({
                "status": delivery.status,
                "pickup_time": delivery.pickup_time,
                "message": "Order picked up"
            })
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='in-transit')
    def in_transit(self, request, pk=None):
        """
        POST /deliveries/{id}/in-transit/
        Transition: picked_up → in_transit
        """
        delivery = self.get_object()
        agent = delivery.agent
        
        if not agent or (request.user != agent.user and not request.user.is_staff):
            return Response(
                {"error": "You are not assigned to this delivery"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            delivery.transition_status(Delivery.Status.IN_TRANSIT)
            return Response({
                "status": delivery.status,
                "message": "Delivery is in transit"
            })
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='deliver')
    def deliver(self, request, pk=None):
        """
        POST /deliveries/{id}/deliver/
        Transition: in_transit → delivered
        Optionally accepts photo URL and customer rating.
        """
        delivery = self.get_object()
        agent = delivery.agent
        
        if not agent or (request.user != agent.user and not request.user.is_staff):
            return Response(
                {"error": "You are not assigned to this delivery"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Optional: allow uploading delivery photo URL
        photo_url = request.data.get('delivery_photo', '')
        if photo_url:
            delivery.delivery_photo = photo_url
        
        try:
            delivery.transition_status(Delivery.Status.DELIVERED)
            # After transition, agent is marked available and total_deliveries incremented
            return Response({
                "status": delivery.status,
                "actual_delivery_time": delivery.actual_delivery_time,
                "message": "Delivery completed"
            })
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='rate')
    def rate(self, request, pk=None):
        """
        POST /deliveries/{id}/rate/
        Customer rates the delivery (1-5 stars) and optional comment.
        Updates agent's average rating.
        """
        delivery = self.get_object()
        order = delivery.order
        
        # Only the customer who placed the order can rate
        if request.user != order.user and not request.user.is_staff:
            return Response(
                {"error": "You can only rate your own deliveries"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if already rated
        if delivery.customer_rating is not None:
            return Response(
                {"error": "This delivery has already been rated"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        rating = request.data.get('rating')
        comment = request.data.get('comment', '')
        
        if rating is None:
            return Response(
                {"error": "rating is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                raise ValueError
        except ValueError:
            return Response(
                {"error": "rating must be an integer between 1 and 5"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        delivery.customer_rating = rating
        delivery.customer_comment = comment
        delivery.save()
        
        # Update agent's average rating
        agent = delivery.agent
        if agent:
            # Recalculate average from all deliveries with ratings
            from django.db.models import Avg
            avg_rating = Delivery.objects.filter(
                agent=agent,
                customer_rating__isnull=False
            ).aggregate(Avg('customer_rating'))['customer_rating__avg']
            agent.rating_avg = avg_rating or 0
            agent.save()
        
        return Response({
            "status": "rated",
            "rating": rating,
            "agent_rating_avg": agent.rating_avg if agent else None
        })

    @action(detail=True, methods=['get'], url_path='track')
    def track(self, request, pk=None):
        """
        GET /deliveries/{id}/track/
        Customer/agent can see current status, agent location (if assigned), and timestamps.
        """
        delivery = self.get_object()
        order = delivery.order
        
        # Allow access to: customer of order, assigned agent, admin
        if request.user != order.user and (not delivery.agent or request.user != delivery.agent.user) and not request.user.is_staff:
            return Response(
                {"error": "You do not have permission to track this delivery"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        data = {
            "delivery_id": delivery.id,
            "order_id": order.id,
            "status": delivery.status,
            "status_display": delivery.get_status_display(),
            "pickup_time": delivery.pickup_time,
            "actual_delivery_time": delivery.actual_delivery_time,
            "delivery_fee": delivery.delivery_fee,
        }
        
        if delivery.agent:
            data["agent"] = {
                "id": delivery.agent.id,
                "full_name": delivery.agent.full_name,
                "vehicle_type": delivery.agent.vehicle_type,
                "current_location": {
                    "type": "Point",
                    "coordinates": [delivery.agent.current_location.x, delivery.agent.current_location.y]
                } if delivery.agent.current_location else None,
                "last_location_update": delivery.agent.last_location_update,
            }
        
        return Response(data)
    

    @action(detail=True, methods=['post'], url_path='ready', permission_classes=[permissions.IsAuthenticated])
    def ready(self, request, pk=None):
        """
        POST /deliveries/{id}/ready/
        Mark delivery as ready for pickup (vendor or admin).
        """
        # Manually fetch delivery – bypass viewset's get_queryset filter
        try:
            delivery = Delivery.objects.get(pk=pk)
        except Delivery.DoesNotExist:
            return Response({"error": "Delivery not found"}, status=status.HTTP_404_NOT_FOUND)

        user = request.user

        # Admin can always mark ready
        if user.is_staff:
            pass
        # Vendor check: does this order contain at least one of their products?
        elif hasattr(user, 'vendor_profile'):
            vendor = user.vendor_profile
            order_items = delivery.order.items.all()
            if not any(item.product.vendor == vendor for item in order_items):
                return Response(
                    {"error": "You are not the vendor for this order"},
                    status=status.HTTP_403_FORBIDDEN
                )
        else:
            return Response(
                {"error": "Only vendor or admin can mark delivery as ready"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Perform status transition
        try:
            delivery.transition_status(Delivery.Status.READY_FOR_PICKUP)
            return Response({
                "status": delivery.status,
                "message": "Delivery is ready for pickup"
            })
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)



    






