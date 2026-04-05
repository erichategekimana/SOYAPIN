from django.db import models
from infrastructure.models import SoftDeleteMixin, TimestampMixin
from django.conf import settings

class InsufficientStockException(Exception):
    pass

class Category(TimestampMixin, models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name_plural = 'categories'

class Vendor(TimestampMixin, models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,  # This references your custom User
        on_delete=models.CASCADE,
        related_name='vendor_profile',
        limit_choices_to={'role': 'vendor'}
    )
    business_name = models.CharField(max_length=255)
    tin_number = models.CharField(max_length=100, blank=True, help_text='Tax Identification Number')
    location_data = models.JSONField(default=dict)  # Can store address, coordinates, etc
    verification_status = models.CharField(max_length=20, default='pending')
    bio = models.TextField(blank=True, help_text='Short description about the vendor')

    class Meta:
        db_table = 'vendors'

    def __str__(self):
        return self.business_name
    @property
    def product_count(self):
        # count only active products
        return self.product.filter(is_published=True, is_deleted=False).count()


class Product(SoftDeleteMixin, TimestampMixin, models.Model):
    vendor = models.ForeignKey('Vendor', on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    image_url = models.URLField(blank=True)
    base_price = models.DecimalField(max_digits=12, decimal_places=2)
    nutritional_data = models.JSONField(default=dict)  # Protein, calories
    is_published = models.BooleanField(default=False)


    @property
    def is_in_stock(self):
        """Returns True if there is at least 1 item available"""
        return self.stock_quantity > 0

    @property
    def current_price(self):
        # Placeholder for future discount logic
        return self.base_price

    @property
    def stock_quantity(self):
        try:
            return self.inventory.quantity_available
        except Inventory.DoesNotExist:
            return 0
    
    # Computed property via annotation
    @property
    def stock_status(self):
        return self.inventory.quantity_available > self.inventory.restock_threshold

class Inventory(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='inventory')
    quantity_available = models.PositiveIntegerField(default=0)
    restock_threshold = models.PositiveIntegerField(default=5)
    expiry_date = models.DateField()
    batch_number = models.CharField(max_length=100, blank=True, null=True)
    
    @property
    def needs_restock(self):
        return self.quantity_available <= self.restock_threshold
    

    def reserve_stock(self, quantity: int) -> bool:
        """Atomic stock reservation"""
        if self.quantity_available >= quantity:
            self.quantity_available -= quantity
            self.save()
            return True
        raise InsufficientStockException(f"Only {self.quantity_available} available")
