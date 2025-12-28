from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from apps.orders.models import Order
from .tasks import send_shipping_notification, send_order_confirmation_email

@receiver(post_save, sender=Order)
def trigger_order_notifications(sender, instance, created, **kwargs):
    """
    Listen for Order saves.
    1. If created -> Send Confirmation Email.
    2. If status changes to SHIPPED -> Send Shipping Email.
    """
    if created:
        # Trigger async task
        send_order_confirmation_email.delay(instance.id)

@receiver(pre_save, sender=Order)
def check_status_change(sender, instance, **kwargs):
    """
    Check if status is changing to SHIPPED.
    Pre_save is used to compare old vs new status.
    """
    if instance.pk:
        try:
            old_order = Order.objects.get(pk=instance.pk)
            if old_order.status != Order.Status.SHIPPED and instance.status == Order.Status.SHIPPED:
                # Trigger async task
                send_shipping_notification.delay(instance.id)
        except Order.DoesNotExist:
            pass