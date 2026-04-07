from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.db.models import Q
from apps.logistics.models import DeliveryAgent
from django.conf import settings


def find_nearest_agent(order, max_distance_km=10):
    """
    Find the nearest available delivery agent to the order's shipping address.
    Returns an agent or None if none found within max_distance_km.
    """
    # Get coordinates from order's shipping address (assumes UserAddress has coordinates)
    address = order.shipping_address
    if not address or not address.coordinates:
        return None

    order_point = address.coordinates  # PointField with geography=True

    # Query available agents (status='available' and is_active=True)
    # Exclude those without current_location
    agents = DeliveryAgent.objects.filter(
        status=DeliveryAgent.Status.AVAILABLE,
        is_active=True,
        current_location__isnull=False
    ).annotate(
        distance=Distance('current_location', order_point)
    ).filter(
        distance__lte=max_distance_km * 1000  # Convert km to meters
    ).order_by('distance')

    return agents.first()




def calculate_delivery_fee(order):
    """
    Calculate delivery fee based on settings.
    Returns Decimal fee (as int or float, but stored as Decimal).
    """
    mode = getattr(settings, 'DELIVERY_FEE_MODE', 'fixed')
    
    if mode == 'fixed':
        fee = getattr(settings, 'DELIVERY_FEE_FIXED_AMOUNT', 1500)
        return fee
    
    elif mode == 'distance':
        address = order.shipping_address
        if not address or not address.coordinates:
            # fallback to fixed fee
            return getattr(settings, 'DELIVERY_FEE_FIXED_AMOUNT', 1500)
        
        warehouse = getattr(settings, 'WAREHOUSE_LOCATION', None)
        if not warehouse:
            # fallback
            return getattr(settings, 'DELIVERY_FEE_FIXED_AMOUNT', 1500)
        
        # Calculate distance in meters
        distance_m = address.coordinates.distance(warehouse)
        distance_km = distance_m / 1000.0
        per_km = getattr(settings, 'DELIVERY_FEE_PER_KM', 500)
        fee = distance_km * per_km
        min_fee = getattr(settings, 'DELIVERY_FEE_MINIMUM', 500)
        return max(fee, min_fee)
    
    return 1500  # fallback






