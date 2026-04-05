from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.db.models import Q
from apps.logistics.models import DeliveryAgent


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