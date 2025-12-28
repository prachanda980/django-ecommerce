from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.utils import timezone
from apps.products.models import Product

User = get_user_model()


class Order(models.Model):
    """Order model with status tracking."""
    
    # Order status choices
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        CONFIRMED = 'confirmed', 'Confirmed'
        SHIPPED = 'shipped', 'Shipped'
        DELIVERED = 'delivered', 'Delivered'
        CANCELLED = 'cancelled', 'Cancelled'
        REFUNDED = 'refunded', 'Refunded'
    
    # Payment status choices
    class PaymentStatus(models.TextChoices):
        PENDING = 'pending', 'Payment Pending'
        COMPLETED = 'completed', 'Payment Completed'
        FAILED = 'failed', 'Payment Failed'
        REFUNDED = 'refunded', 'Payment Refunded'
    
    # Core order fields
    order_number = models.CharField(max_length=50, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    
    # Pricing fields
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Customer information
    shipping_address = models.TextField()
    billing_address = models.TextField()
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=20)
    
    # Payment information
    payment_method = models.CharField(max_length=50)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    shipped_at = models.DateTimeField(blank=True, null=True)
    delivered_at = models.DateTimeField(blank=True, null=True)
    
    # Additional fields
    notes = models.TextField(blank=True)
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    coupon_code = models.CharField(max_length=50, blank=True, null=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['payment_status']),
        ]

    def __str__(self):
        return f"Order {self.order_number}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)

    def generate_order_number(self):
        """Generate a unique order number."""
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        user_id = str(self.user.id).zfill(6)
        return f"ORD{timestamp}{user_id}"

    def calculate_total(self):
        """Calculate order total."""
        self.subtotal = sum(item.subtotal for item in self.items.all())
        self.total = self.subtotal + self.tax + self.shipping - self.discount_amount
        return self.total

    def can_cancel(self):
        """Check if order can be cancelled."""
        return self.status in [self.Status.PENDING, self.Status.CONFIRMED]

    def can_refund(self):
        """Check if order can be refunded."""
        return self.status == self.Status.DELIVERED and self.payment_status == self.PaymentStatus.COMPLETED


class OrderItem(models.Model):
    """Individual items within an order."""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Additional fields for tracking
    product_name_at_purchase = models.CharField(max_length=200)
    product_sku_at_purchase = models.CharField(max_length=100)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.quantity}x {self.product.name} in Order {self.order.order_number}"

    def save(self, *args, **kwargs):
        # Store product details at time of purchase
        if not self.product_name_at_purchase:
            self.product_name_at_purchase = self.product.name
        if not self.product_sku_at_purchase:
            self.product_sku_at_purchase = self.product.sku
        
        # Calculate subtotal
        self.subtotal = self.quantity * self.unit_price
        super().save(*args, **kwargs)


class OrderStatusHistory(models.Model):
    """Track order status changes for audit trail."""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
    old_status = models.CharField(max_length=20, choices=Order.Status.choices)
    new_status = models.CharField(max_length=20, choices=Order.Status.choices)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order {self.order.order_number}: {self.old_status} → {self.new_status}"


class Payment(models.Model):
    """Payment transactions for orders."""
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    payment_method = models.CharField(max_length=50)
    transaction_id = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=20, choices=Order.PaymentStatus.choices)
    
    # Payment provider details
    provider = models.CharField(max_length=50)
    provider_response = models.JSONField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment {self.transaction_id} for Order {self.order.order_number}"