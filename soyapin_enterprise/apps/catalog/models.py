from infrastructure.models import SoftDeleteMixin, TimestampMixin

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    
    class Meta:
        verbose_name_plural = 'categories'

class Product(SoftDeleteMixin, TimestampMixin):
    vendor = models.ForeignKey('identity.Vendor', on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=255)
    base_price = models.DecimalField(max_digits=12, decimal_places=2)
    nutritional_data = models.JSONField(default=dict)  # Protein, calories
    
    # Computed property via annotation
    @property
    def stock_status(self):
        return self.inventory.quantity_available > self.inventory.restock_threshold

class Inventory(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='inventory')
    quantity = models.PositiveIntegerField(default=0)
    threshold = models.PositiveIntegerField(default=5)
    expiry_date = models.DateField()
    
    def reserve_stock(self, quantity: int) -> bool:
        """Atomic stock reservation"""
        if self.quantity >= quantity:
            self.quantity -= quantity
            self.save()
            return True
        raise InsufficientStockException(f"Only {self.quantity} available")
