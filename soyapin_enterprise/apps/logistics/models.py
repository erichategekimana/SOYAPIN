from django.contrib.gis.db.models import PointField

class DeliveryAgent(models.Model):
    user = models.OneToOneField('identity.User', on_delete=models.CASCADE)
    vehicle_type = models.CharField(max_length=50)
    current_location = PointField(geography=True, null=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    is_available = models.BooleanField(default=True)
    
    def find_nearby_orders(self, radius_km: int = 5):
        """GeoQuery: Find orders within radius"""
        return Order.objects.filter(
            delivery__isnull=True,
            user__addresses__coordinates__dwithin=(self.current_location, radius_km * 1000)
        )
