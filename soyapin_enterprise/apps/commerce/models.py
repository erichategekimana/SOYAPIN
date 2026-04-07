from django.db import models, transaction
from django.core.validators import MinValueValidator
from decimal import Decimal

from infrastructure.models.abstract_models import TimestampMixin
from apps.identity.models import User, UserAddress
from apps.catalog.models import Product, Inventory


class InsufficientStockException(Exception):
    pass


class Cart(TimestampMixin, models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='cart'
    )
    
    class Meta:
        db_table = 'carts'
    

    def to_order(self, shipping_address, notes=""):
        """
        Converts the current cart into a confirmed Order.
        """
        with transaction.atomic():
            # 1. Create the Order object
            order = Order.objects.create(
                user=self.user,
                shipping_address=shipping_address,
                notes=notes,
                total_amount=self.total
            )

            # 2. Convert CartItems to OrderItems and reserve stock
            for item in self.items.all():
                # Reserve the stock (this also handles the InsufficientStockException)
                item.product.inventory.reserve_stock(item.quantity)

                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    unit_price=item.unit_price # Snapshots the price
                )

            # 3. Clear the cart after successful order creation
            self.clear()
            
            return order
        

    def get_total_protein(self):
        """Returns total protein in grams for all cart items."""
        total = 0
        for item in self.items.all():
            protein = item.product.nutritional_data.get('protein', 0)
            total += item.quantity * protein
        return total

    def get_total_calories(self):
        """Returns total calories for all cart items."""
        total = 0
        for item in self.items.all():
            calories = item.product.nutritional_data.get('calories', 0)
            total += item.quantity * calories
        return total

    def get_protein_percentage(self, user):
        """Returns percentage of user's daily protein goal, or None if no health profile."""
        if not hasattr(user, 'health_profile'):
            return None
        goal = user.health_profile.daily_protein_goal_g
        if goal <= 0:
            return None
        total_protein = self.get_total_protein()
        return round((total_protein / goal) * 100, 1)


    @property
    def total(self):
        return sum(item.subtotal for item in self.items.all())
    
    @property
    def item_count(self):
        return sum(item.quantity for item in self.items.all())
    
    def clear(self):
        self.items.all().delete()
    
    def add_item(self, product, quantity=1):
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        
        if product.stock_quantity < quantity:
            raise InsufficientStockException(
                f"Only {product.stock_quantity} available"
            )
        
        cart_item, created = CartItem.objects.get_or_create(
            cart=self,
            product=product,
            defaults={'quantity': quantity, 'unit_price': product.current_price}
        )
        
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
        
        return cart_item


class CartItem(TimestampMixin, models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    
    class Meta:
        db_table = 'cart_items'
        unique_together = ['cart', 'product']
    
    @property
    def subtotal(self):
        if self.quantity is not None and self.unit_price is not None:
            return self.quantity * self.unit_price
        return 0
    
    def save(self, *args, **kwargs):
        if not self.unit_price:
            self.unit_price = self.product.current_price
        super().save(*args, **kwargs)


class Order(TimestampMixin, models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PAID = 'paid', 'Paid'
        PROCESSING = 'processing', 'Processing'
        SHIPPED = 'shipped', 'Shipped'
        DELIVERED = 'delivered', 'Delivered'
        CANCELLED = 'cancelled', 'Cancelled'
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    shipping_address = models.ForeignKey(UserAddress, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'orders'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Order #{self.id} - {self.status}"
    
    @property
    def item_count(self):
        return sum(item.quantity for item in self.items.all())


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    
    class Meta:
        db_table = 'order_items'
    
    @property
    def subtotal(self):
        if self.quantity is not None and self.unit_price is not None:
            return self.quantity * self.unit_price
        return 0
    
    def save(self, *args, **kwargs):
        if not self.unit_price and self.product:
            self.unit_price = self.product.current_price
        super().save(*args, **kwargs)


class Payment(TimestampMixin, models.Model):
    class Provider(models.TextChoices):
        MTN = 'mtn', 'MTN Mobile Money'
        AIRTEL = 'airtel', 'Airtel Money'
        EQUITY = 'equity', 'Equity Bank'
        CASH = 'cash', 'Cash on Delivery'
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        REFUNDED = 'refunded', 'Refunded'
    
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    provider = models.CharField(max_length=20, choices=Provider.choices)
    transaction_ref = models.CharField(max_length=255, unique=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    completed_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True)
    
    class Meta:
        db_table = 'payments'
    
    def confirm(self):
        from django.utils import timezone
        if self.status != self.Status.PENDING:
            raise ValueError("Payment already processed")
        
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.save()
        
        # Update order
        self.order.status = Order.Status.PAID
        self.order.save()