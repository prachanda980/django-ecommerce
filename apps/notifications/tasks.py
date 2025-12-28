from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.conf import settings
import logging

# Use lazy imports inside tasks to avoid circular dependencies
from apps.orders.models import Order, OrderItem

User = get_user_model()
logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def send_order_confirmation_email(self, order_id):
    """
    Send order confirmation email asynchronously.
    """
    try:
        order = Order.objects.select_related('user').get(id=order_id)
        order_items = OrderItem.objects.filter(order=order).select_related('product')
        
        context = {
            'order': order,
            'user': order.user,
            'order_items': order_items,
            'current_date': timezone.now()
        }
        
        subject = f"Order Confirmation - {order.order_number}"
        # Make sure these templates exist in your templates folder
        html_message = render_to_string('emails/order_confirmation.html', context)
        text_message = render_to_string('emails/order_confirmation.txt', context)
        
        send_mail(
            subject=subject,
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.customer_email],
            html_message=html_message,
            fail_silently=False
        )
        
        logger.info(f"EMAIL SENT: Order confirmation for {order.order_number}")
        return True
        
    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found.")
        return False
    except Exception as e:
        logger.error(f"Failed to send email for order {order_id}: {e}")
        raise self.retry(exc=e, countdown=60)

@shared_task(bind=True, max_retries=3)
def send_shipping_notification(self, order_id):
    """
    Send email when order status changes to SHIPPED.
    """
    try:
        order = Order.objects.get(id=order_id)
        
        context = {
            'order': order,
            'tracking_number': order.tracking_number,
        }
        
        subject = f"Your Order {order.order_number} has Shipped!"
        html_message = render_to_string('emails/shipping_notification.html', context)
        text_message = render_to_string('emails/shipping_notification.txt', context)
        
        send_mail(
            subject=subject,
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.customer_email],
            html_message=html_message
        )
        return True
    except Exception as e:
        logger.error(f"Shipping email failed: {e}")
        raise self.retry(exc=e, countdown=60)

@shared_task
def update_trending_products():
    """
    Recalculate trending products based on last 7 days of sales.
    """
    from django.core.cache import cache
    from django.db.models import Count, Sum
    from datetime import timedelta
    
    try:
        date_from = timezone.now() - timedelta(days=7)
        
        # Aggregate sales data
        trending = (
            OrderItem.objects
            .filter(order__created_at__gte=date_from)
            .values('product_id', 'product__name', 'product__price')
            .annotate(total_sold=Sum('quantity'))
            .order_by('-total_sold')[:10]
        )
        
        trending_data = list(trending)
        
        # Cache for 1 hour
        cache.set('trending_products', trending_data, 3600)
        logger.info(f"CACHE UPDATED: {len(trending_data)} trending products.")
        return len(trending_data)
        
    except Exception as e:
        logger.error(f"Trending update failed: {e}")
        return 0

@shared_task
def cleanup_abandoned_carts():
    """
    Release stock from carts inactive for > 30 mins.
    """
    # Import inside function to prevent circular import with apps.cart
    try:
        from apps.cart.models import Cart, CartItem
    except ImportError:
        logger.warning("Cart app not found, skipping cleanup.")
        return

    cutoff = timezone.now() - timezone.timedelta(minutes=30)
    
    # Find active carts that are old
    old_carts = Cart.objects.filter(updated_at__lt=cutoff, is_active=True)
    count = 0
    
    for cart in old_carts:
        items = CartItem.objects.filter(cart=cart)
        for item in items:
            # Logic to return stock if you reserved it strictly on 'add to cart'
            # (Note: In your SRS, you reserve on Checkout, but if you reserve on Add To Cart, this is needed)
            if hasattr(item.product, 'release_reserved_stock'):
                item.product.release_reserved_stock(item.quantity)
        
        cart.is_active = False
        cart.save()
        count += 1
        
    logger.info(f"CLEANUP: Deactivated {count} abandoned carts.")