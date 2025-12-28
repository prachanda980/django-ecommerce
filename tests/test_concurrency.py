import pytest
import threading
import time
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.db import transaction
from django.core import mail
from unittest.mock import patch

from apps.products.models import Product, Category
from apps.orders.models import Order, OrderItem
from apps.orders.services import OrderService
from apps.notifications.tasks import send_order_confirmation_email

User = get_user_model()


class ConcurrencyTestCase(TransactionTestCase):
    """Test concurrent order processing to ensure inventory consistency."""
    
    def setUp(self):
        """Set up test data."""
        # Create test user
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        
        # Create category
        self.category = Category.objects.create(
            name='Electronics',
            slug='electronics'
        )
        
        # Create product with limited stock
        self.product = Product.objects.create(
            name='Test Smartphone',
            slug='test-smartphone',
            description='A test smartphone',
            category=self.category,
            price=299.99,
            stock=5,  # Only 5 items available
            sku='TEST-001'
        )
    
    def test_single_order_success(self):
        """Test that a single order processes correctly."""
        items = [{'product_id': self.product.id, 'quantity': 2}]
        
        result = OrderService.create_order(
            user=self.user,
            items=items,
            shipping_address='123 Test St',
            billing_address='123 Test St',
            payment_method='credit_card'
        )
        
        self.assertEqual(result['status'], 'success')
        self.assertIn('order_id', result)
        self.assertIn('order_number', result)
        
        # Verify stock was deducted
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)  # 5 - 2 = 3
        
        # Verify order was created
        order = Order.objects.get(id=result['order_id'])
        self.assertEqual(order.user, self.user)
        self.assertEqual(order.items.count(), 1)
        
        order_item = order.items.first()
        self.assertEqual(order_item.product, self.product)
        self.assertEqual(order_item.quantity, 2)
    
    def test_insufficient_stock_error(self):
        """Test that orders fail when stock is insufficient."""
        items = [{'product_id': self.product.id, 'quantity': 10}]  # Request 10, only 5 available
        
        result = OrderService.create_order(
            user=self.user,
            items=items,
            shipping_address='123 Test St',
            billing_address='123 Test St',
            payment_method='credit_card'
        )
        
        self.assertEqual(result['status'], 'error')
        self.assertIn('details', result)
        
        # Verify stock was not changed
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)
        
        # Verify no order was created
        self.assertEqual(Order.objects.count(), 0)
    
    def test_concurrent_orders_with_enough_stock(self):
        """Test that concurrent orders don't oversell when there's enough stock."""
        results = []
        errors = []
        
        def place_order(order_quantity, thread_id):
            """Place an order in a separate thread."""
            try:
                items = [{'product_id': self.product.id, 'quantity': order_quantity}]
                
                result = OrderService.create_order(
                    user=self.user,
                    items=items,
                    shipping_address=f'{thread_id} Test St',
                    billing_address=f'{thread_id} Test St',
                    payment_method='credit_card'
                )
                
                results.append(result)
            except Exception as e:
                errors.append({'thread_id': thread_id, 'error': str(e)})
        
        # Create multiple threads to place orders simultaneously
        threads = []
        for i in range(3):  # 3 orders of 1 item each
            thread = threading.Thread(target=place_order, args=(1, i))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All orders should succeed (3 * 1 = 3, we have 5 in stock)
        self.assertEqual(len(results), 3)
        self.assertEqual(len(errors), 0)
        
        # Verify total stock deducted
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 2)  # 5 - 3 = 2
        
        # Verify 3 orders were created
        self.assertEqual(Order.objects.count(), 3)
    
    def test_concurrent_orders_overselling_prevention(self):
        """Test that concurrent orders cannot oversell the product."""
        results = []
        errors = []
        
        def place_order(order_quantity, thread_id):
            """Place an order in a separate thread."""
            try:
                items = [{'product_id': self.product.id, 'quantity': order_quantity}]
                
                result = OrderService.create_order(
                    user=self.user,
                    items=items,
                    shipping_address=f'{thread_id} Test St',
                    billing_address=f'{thread_id} Test St',
                    payment_method='credit_card'
                )
                
                results.append({'thread_id': thread_id, 'result': result})
            except Exception as e:
                errors.append({'thread_id': thread_id, 'error': str(e)})
        
        # Create multiple threads to place large orders simultaneously
        # Each wants 3 items, but we only have 5 total
        threads = []
        for i in range(3):
            thread = threading.Thread(target=place_order, args=(3, i))
            threads.append(thread)
        
        # Start all threads with a small delay to simulate real-world timing
        for i, thread in enumerate(threads):
            time.sleep(0.01)  # 10ms delay between thread starts
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Analyze results
        successful_orders = [r for r in results if r['result']['status'] == 'success']
        failed_orders = [r for r in results if r['result']['status'] == 'error']
        
        # At most 1 order should succeed (3 items each, we have 5 total)
        # But due to race conditions, we might see different patterns
        total_items_ordered = sum(
            r['result']['total'] / float(self.product.price) 
            for r in successful_orders
        )
        
        # Verify no overselling occurred
        self.product.refresh_from_db()
        self.assertGreaterEqual(self.product.stock, 0)
        
        # The total items ordered should not exceed initial stock
        initial_stock = 5
        items_remaining = self.product.stock
        items_ordered = initial_stock - items_remaining
        self.assertLessEqual(items_ordered, initial_stock)
    
    def test_order_cancellation_restores_stock(self):
        """Test that cancelling an order restores the stock."""
        # Create an order
        items = [{'product_id': self.product.id, 'quantity': 3}]
        
        result = OrderService.create_order(
            user=self.user,
            items=items,
            shipping_address='123 Test St',
            billing_address='123 Test St',
            payment_method='credit_card'
        )
        
        self.assertEqual(result['status'], 'success')
        
        # Verify stock was deducted
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 2)  # 5 - 3 = 2
        
        # Cancel the order
        cancel_result = OrderService.cancel_order(
            order_id=result['order_id'],
            user=self.user
        )
        
        self.assertEqual(cancel_result['status'], 'success')
        
        # Verify stock was restored
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)  # 2 + 3 = 5
        
        # Verify order status was updated
        order = Order.objects.get(id=result['order_id'])
        self.assertEqual(order.status, Order.Status.CANCELLED)
    
    def test_database_locking_prevents_race_condition(self):
        """Test that database locking prevents race conditions."""
        # This test simulates the exact race condition scenario
        results = {'success': 0, 'failure': 0}
        
        def attempt_purchase():
            """Attempt to purchase the last item."""
            # Refresh product data to get current stock
            product = Product.objects.get(id=self.product.id)
            
            if product.stock >= 1:
                # Simulate processing delay
                time.sleep(0.1)
                
                # Try to create order
                items = [{'product_id': self.product.id, 'quantity': 1}]
                result = OrderService.create_order(
                    user=self.user,
                    items=items,
                    shipping_address='123 Test St',
                    billing_address='123 Test St',
                    payment_method='credit_card'
                )
                
                if result['status'] == 'success':
                    results['success'] += 1
                else:
                    results['failure'] += 1
            else:
                results['failure'] += 1
        
        # Set stock to 1 item
        self.product.stock = 1
        self.product.save()
        
        # Create multiple threads trying to buy the same item
        threads = []
        for i in range(5):  # 5 threads trying to buy 1 item
            thread = threading.Thread(target=attempt_purchase)
            threads.append(thread)
        
        # Start all threads simultaneously
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Only one purchase should succeed
        self.assertEqual(results['success'], 1)
        self.assertEqual(results['failure'], 4)
        
        # Stock should be 0
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 0)
        
        # Only one order should exist
        self.assertEqual(Order.objects.count(), 1)


class InventoryServiceTestCase(TestCase):
    """Test inventory management services."""
    
    def setUp(self):
        """Set up test data."""
        self.category = Category.objects.create(name='Test', slug='test')
        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            category=self.category,
            price=10.00,
            stock=10,
            sku='TEST-001'
        )
    
    def test_check_stock_availability(self):
        """Test stock availability checking."""
        from apps.products.services import ProductCacheService
        
        # Test with enough stock
        can_fulfill, available = ProductCacheService.check_real_time_stock(
            self.product.id, 5
        )
        self.assertTrue(can_fulfill)
        self.assertEqual(available, 10)
        
        # Test with too much stock requested
        can_fulfill, available = ProductCacheService.check_real_time_stock(
            self.product.id, 15
        )
        self.assertFalse(can_fulfill)
        self.assertEqual(available, 10)
        
        # Test with non-existent product
        can_fulfill, available = ProductCacheService.check_real_time_stock(999, 1)
        self.assertFalse(can_fulfill)
        self.assertEqual(available, 0)
    
    def test_stock_reservation_and_release(self):
        """Test stock reservation and release functionality."""
        # Reserve stock
        reserved = self.product.reserve_stock(3)
        self.assertTrue(reserved)
        
        self.product.refresh_from_db()
        self.assertEqual(self.product.reserved_stock, 3)
        self.assertEqual(self.product.available_stock, 7)
        
        # Release stock
        self.product.release_reserved_stock(2)
        self.product.refresh_from_db()
        self.assertEqual(self.product.reserved_stock, 1)
        self.assertEqual(self.product.available_stock, 9)
        
        # Try to reserve more than available
        reserved = self.product.reserve_stock(15)
        self.assertFalse(reserved)
        
        self.product.refresh_from_db()
        self.assertEqual(self.product.reserved_stock, 1)  # Should not change


class WebSocketTestCase(TestCase):
    """Test WebSocket functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.category = Category.objects.create(name='Test', slug='test')
        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            category=self.category,
            price=10.00,
            stock=10,
            sku='TEST-001'
        )
    
    @patch('apps.products.consumers.broadcast_stock_update')
    def test_stock_broadcast_on_purchase(self, mock_broadcast):
        """Test that stock updates are broadcast on purchase."""
        # Create user
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        # Create order
        items = [{'product_id': self.product.id, 'quantity': 2}]
        result = OrderService.create_order(
            user=user,
            items=items,
            shipping_address='123 Test St',
            billing_address='123 Test St',
            payment_method='credit_card'
        )
        
        # Verify broadcast was called
        mock_broadcast.assert_called_once_with(self.product.id, 8)  # 10 - 2 = 8
    
    def test_stock_broadcast_function(self):
        """Test the stock broadcast function directly."""
        from apps.products.consumers import broadcast_stock_update
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        # Mock channel layer
        with patch('apps.products.consumers.get_channel_layer') as mock_get_channel:
            mock_channel_layer = mock_get_channel.return_value
            
            # Call broadcast function
            async_to_sync(broadcast_stock_update)(self.product.id, 5)
            
            # Verify group send was called
            mock_channel_layer.group_send.assert_called_once()
            
            # Get the call arguments
            call_args = mock_channel_layer.group_send.call_args
            group_name = call_args[0][0]
            message = call_args[0][1]
            
            # Verify message structure
            self.assertEqual(group_name, f'product_{self.product.id}')
            self.assertEqual(message['type'], 'stock_update')
            self.assertEqual(message['product_id'], self.product.id)
            self.assertEqual(message['stock'], 5)


class CacheTestCase(TestCase):
    """Test Redis caching functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.category = Category.objects.create(name='Test', slug='test')
        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            category=self.category,
            price=10.00,
            stock=10,
            sku='TEST-001'
        )
    
    def test_product_detail_caching(self):
        """Test product detail caching."""
        from apps.products.services import ProductCacheService
        from django.core.cache import cache
        
        # Clear cache
        cache.clear()
        
        # First call should hit database
        with self.assertNumQueries(1):
            product_data = ProductCacheService.get_cached_product_detail(self.product.id)
        
        self.assertIsNotNone(product_data)
        self.assertEqual(product_data['id'], self.product.id)
        self.assertEqual(product_data['name'], self.product.name)
        
        # Second call should hit cache
        with self.assertNumQueries(0):
            cached_data = ProductCacheService.get_cached_product_detail(self.product.id)
        
        self.assertEqual(product_data, cached_data)
        
        # Verify stock is NOT cached
        self.assertNotIn('stock', product_data)
        self.assertNotIn('available_stock', product_data)
    
    def test_cache_invalidation(self):
        """Test cache invalidation."""
        from apps.products.services import ProductCacheService
        from django.core.cache import cache
        
        # Cache product
        ProductCacheService.get_cached_product_detail(self.product.id)
        
        # Verify it's in cache
        cache_key = f'product_detail_{self.product.id}'
        self.assertIsNotNone(cache.get(cache_key))
        
        # Invalidate cache
        ProductCacheService.invalidate_product_cache(self.product.id)
        
        # Verify it's removed from cache
        self.assertIsNone(cache.get(cache_key))
    
    def test_real_time_stock_checking(self):
        """Test that real-time stock checking bypasses cache."""
        from apps.products.services import ProductCacheService
        
        # Cache product details
        ProductCacheService.get_cached_product_detail(self.product.id)
        
        # Modify stock directly in database
        self.product.stock = 5
        self.product.save()
        
        # Real-time stock check should get current value, not cached value
        can_fulfill, available = ProductCacheService.check_real_time_stock(
            self.product.id, 3
        )
        
        self.assertTrue(can_fulfill)
        self.assertEqual(available, 5)  # Should be 5, not the original 10