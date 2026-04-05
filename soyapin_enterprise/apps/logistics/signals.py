from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.commerce.models import Order
from apps.logistics.models import Delivery
from apps.logistics.services import find_nearest_agent


@receiver(post_save, sender=Order)
def create_delivery_on_order_paid(sender, instance, created, **kwargs):
    """
    When an order becomes PAID, create a Delivery record and try to assign an agent.
    """
    # Only trigger when status changes to PAID (not on initial creation)
    # We need to detect transition. Use a signal that checks old status? 
    # Simpler: check if order is PAID and delivery does not exist yet.
    if instance.status == Order.Status.PAID and not hasattr(instance, 'delivery'):
        delivery = Delivery.objects.create(
            order=instance,
            status=Delivery.Status.PREPARING,
            delivery_fee=0.00  # Will be calculated later in Step 7
        )
        # Try to assign an agent
        agent = find_nearest_agent(instance)
        if agent:
            delivery.agent = agent
            delivery.save()
            agent.mark_busy()  # Agent becomes busy