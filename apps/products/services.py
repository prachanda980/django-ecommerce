import logging
from datetime import timedelta
from django.core.cache import cache
from django.utils import timezone
from django.db import models
from .models import Product, Category

logger = logging.getLogger(__name__)

class ProductCacheService:
    """
    Handles caching for Product reads.
    CRITICAL: Never use cache for stock validation during checkout.
    """
    TTL_DETAIL = 3600  # 1 hour
    TTL_LIST = 1800    # 30 mins
    
    @staticmethod
    def get_cached_product_detail(product_id):
        key = f'product_detail_{product_id}'
        data = cache.get(key)
        
        if data:
            return data
            
        try:
            product = Product.objects.select_related('category').get(id=product_id, is_active=True)
            data = {
                'id': product.id,
                'name': product.name,
                'slug': product.slug,
                'description': product.description,
                'price': str(product.price),
                'category': {'name': product.category.name, 'slug': product.category.slug},
                'image': product.image.url if product.image else None,
                # NOTE: We do not cache 'stock' here to avoid showing stale data.
                # Stock is fetched real-time via API or WebSocket.
            }
            cache.set(key, data, ProductCacheService.TTL_DETAIL)
            return data
        except Product.DoesNotExist:
            return None

    @staticmethod
    def invalidate_product_cache(product_id):
        """Call this on Product save/delete."""
        cache.delete(f'product_detail_{product_id}')
        # Optional: Invalidate list caches if needed
        cache.delete_pattern("product_list_*")

    @staticmethod
    def check_real_time_stock(product_id, quantity):
        """
        Direct DB hit for critical stock checks. 
        Bypasses all caches.
        """
        try:
            product = Product.objects.get(id=product_id)
            is_available = product.available_stock >= quantity
            return is_available, product.available_stock
        except Product.DoesNotExist:
            return False, 0

    @staticmethod
    def get_cached_trending_products():
        key = 'trending_products'
        data = cache.get(key)
        if data:
            return data
            
        # Lazy import to avoid circular dependency with Orders app
        from apps.orders.models import Order, OrderItem
        
        last_week = timezone.now() - timedelta(days=7)
        
        trending = (
            OrderItem.objects.filter(order__created_at__gte=last_week)
            .values('product_id', 'product__name', 'product__slug', 'product__price')
            .annotate(sales_count=models.Count('id'))
            .order_by('-sales_count')[:10]
        )
        
        data = list(trending)
        cache.set(key, data, 3600)
        return data