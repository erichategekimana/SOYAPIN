from django.db import models
from django.contrib.gis.db.models import PointField
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings

from infrastructure.models.abstract_models import TimestampMixin
from apps.commerce.models import Order


class DeliveryAgent(TimestampMixin, models.Model):
    """
    Delivery personnel - matches SQL: agents table with PostGIS location
    """
    class Status(models.TextChoices):
        AVAILABLE = 'available', 'Available'
        BUSY = 'busy', 'Busy'
        OFFLINE = 'offline', 'Offline'
    
    class VehicleType(models.TextChoices):
        BICYCLE = 'bicycle', 'Bicycle'
        MOTORCYCLE = 'motorcycle', 'Motorcycle'
        CAR = 'car', 'Car'
        VAN = 'van', 'Van'
    
    # Link to User (agent must have role='agent')
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='agent_profile',
        limit_choices_to={'role': 'agent'}
    )
    
    assigned_zone = models.CharField(
        max_length=100,
        blank=True,
        help_text='Delivery area/zone (e.g., Kigali-North, Kigali-Central)'
    )

    profile_picture = models.URLField(
        upload_to='agent_profiles/',
        null=True,
        help_text='Profile picture of the delivery agent'
    )
    
    vehicle_type = models.CharField(
        max_length=20,
        choices=VehicleType.choices,
        default=VehicleType.MOTORCYCLE
    )
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.AVAILABLE
    )
    
    rating_avg = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0.00), MaxValueValidator(5.00)]
    )
    
    total_deliveries = models.PositiveIntegerField(default=0)
    
    # PostGIS location tracking
    current_location = PointField(
        geography=True,
        null=True,
        blank=True,
        help_text='Current GPS coordinates'
    )
    
    last_location_update = models.DateTimeField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'agents'
        ordering = ['-rating_avg', 'total_deliveries']
    
    def __str__(self):
        return f"{self.user.full_name} - {self.assigned_zone} ({self.status})"
    
    @property
    def full_name(self):
        return self.user.full_name or self.user.email
    
    def update_location(self, lat, lng):
        """Update agent location with timestamp"""
        from django.utils import timezone
        from django.contrib.gis.geos import Point
        
        self.current_location = Point(lng, lat)  # PostGIS uses (lon, lat)
        self.last_location_update = timezone.now()
        self.save()
    
    def mark_busy(self):
        self.status = self.Status.BUSY
        self.save()
    
    def mark_available(self):
        self.status = self.Status.AVAILABLE
        self.save()


class Delivery(TimestampMixin, models.Model):
    """
    Order fulfillment - matches SQL: deliveries table
    Links Order to DeliveryAgent with status tracking
    """
    class Status(models.TextChoices):
        PREPARING = 'preparing', 'Preparing'
        READY_FOR_PICKUP = 'ready_for_pickup', 'Ready for Pickup'
        PICKED_UP = 'picked_up', 'Picked Up'
        IN_TRANSIT = 'in_transit', 'In Transit'
        DELIVERED = 'delivered', 'Delivered'
        CANCELLED = 'cancelled', 'Cancelled'
    
    # Link to Order (one-to-one: one order has one delivery)
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='delivery'
    )
    
    # Assigned agent (can be null initially, assigned later)
    agent = models.ForeignKey(
        DeliveryAgent,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deliveries'
    )
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PREPARING
    )
    
    pickup_time = models.DateTimeField(null=True, blank=True)
    actual_delivery_time = models.DateTimeField(null=True, blank=True)
    
    delivery_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00
    )
    
    # Customer rating of delivery
    customer_rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    
    customer_comment = models.TextField(blank=True)
    
    # Proof of delivery (photo URL)
    delivery_photo = models.URLField(blank=True, max_length=500)
    
    class Meta:
        db_table = 'deliveries'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Delivery #{self.id} - Order #{self.order.id} - {self.status}"
    
    def can_transition_to(self, new_status):
        """Valid status transitions"""
        valid_transitions = {
            self.Status.PREPARING: [self.Status.READY_FOR_PICKUP, self.Status.CANCELLED],
            self.Status.READY_FOR_PICKUP: [self.Status.PICKED_UP, self.Status.CANCELLED],
            self.Status.PICKED_UP: [self.Status.IN_TRANSIT, self.Status.CANCELLED],
            self.Status.IN_TRANSIT: [self.Status.DELIVERED, self.Status.CANCELLED],
            self.Status.DELIVERED: [],
            self.Status.CANCELLED: [],
        }
        return new_status in valid_transitions.get(self.status, [])
    
    def transition_status(self, new_status):
        from django.utils import timezone
        from django.apps import apps

        if not self.can_transition_to(new_status):
            raise ValueError(f"Cannot transition from {self.status} to {new_status}")

        old_status = self.status
        self.status = new_status

        if new_status == self.Status.PICKED_UP and not self.pickup_time:
            self.pickup_time = timezone.now()
        elif new_status == self.Status.DELIVERED and not self.actual_delivery_time:
            self.actual_delivery_time = timezone.now()
            if self.agent:
                self.agent.total_deliveries += 1
                self.agent.mark_available()
                self.agent.save()
                # Auto-create pending payout
                AgentPayout = apps.get_model('logistics', 'AgentPayout')
                AgentPayout.objects.create(
                    agent=self.agent,
                    amount=self.delivery_fee,   # full fee goes to agent (adjust as needed)
                    description=f"Delivery #{self.id} for Order #{self.order.id}",
                    status=AgentPayout.Status.PENDING
                )

        self.save()
        return True


class AgentPayout(TimestampMixin, models.Model):
    """
    Financial records for agent commissions - matches SQL: agent_payouts
    """
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
    
    agent = models.ForeignKey(
        DeliveryAgent,
        on_delete=models.CASCADE,
        related_name='payouts'
    )
    
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    
    processed_at = models.DateTimeField(null=True, blank=True)
    
    # Reference to period or deliveries included
    description = models.TextField(blank=True)
    
    transaction_reference = models.CharField(max_length=255, blank=True)
    
    class Meta:
        db_table = 'agent_payouts'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Payout {self.agent.full_name} - {self.amount} - {self.status}"
    
    def mark_completed(self, reference):
        """Mark payout as completed"""
        from django.utils import timezone
        
        self.status = self.Status.COMPLETED
        self.processed_at = timezone.now()
        self.transaction_reference = reference
        self.save()