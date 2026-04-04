from django_fsm import FSMField, transition

class Order(TimestampMixin):
    class Status(models.TextChoices):
        PENDING = 'pending'
        PAID = 'paid'
        PROCESSING = 'processing'
        SHIPPED = 'shipped'
        DELIVERED = 'delivered'
    
    user = models.ForeignKey('identity.User', on_delete=models.CASCADE)
    status = FSMField(default=Status.PENDING, choices=Status.choices)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    
    @transition(field=status, source=Status.PENDING, target=Status.PAID)
    def process_payment(self, transaction_id: str):
        """State machine transition"""
        Payment.objects.create(
            order=self,
            transaction_ref=transaction_id,
            amount=self.total
        )

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey('catalog.Product', on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)  # Snapshot price
    
    def save(self, *args, **kwargs):
        if not self.unit_price:
            self.unit_price = self.product.base_price
        super().save(*args, **kwargs)
