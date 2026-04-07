from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.commerce.models import Order
from apps.logistics.models import Delivery
from apps.logistics.services import find_nearest_agent, calculate_delivery_fee


@receiver(post_save, sender=Order)
def create_delivery_on_order_paid(sender, instance, created, **kwargs):
    """
    When an order becomes PAID, create a Delivery record and try to assign an agent.
    """
    if instance.status == Order.Status.PAID and not hasattr(instance, 'delivery'):
        fee = calculate_delivery_fee(instance)
        delivery = Delivery.objects.create(
            order=instance,
            status=Delivery.Status.PREPARING,
            delivery_fee=fee
        )
        agent = find_nearest_agent(instance)
        if agent:
            delivery.agent = agent
            delivery.save()
            agent.mark_busy()