from django.contrib import admin
from django.utils.html import format_html
from .models import Order, OrderItem, OrderStatusHistory, Payment

# 1. Inline for Order Items (View products inside the Order page)
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    # Users shouldn't change product details once purchased
    readonly_fields = ('product', 'quantity', 'unit_price', 'subtotal', 'product_name_at_purchase')
    extra = 0
    can_delete = False

# 2. Inline for Status History (Audit trail)
class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    readonly_fields = ('old_status', 'new_status', 'changed_by', 'reason', 'created_at')
    extra = 0
    can_delete = False
    classes = ['collapse'] # Keep it hidden unless needed

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    # --- 3. List View Customization ---
    list_display = [
        'order_number', 'user_link', 'status_badge', 
        'payment_status_badge', 'total_display', 'created_at'
    ]
    list_filter = ['status', 'payment_status', 'created_at', 'payment_method']
    search_fields = ['order_number', 'customer_email', 'customer_phone', 'user__email']
    list_per_page = 25

    # --- 4. Form Layout (Organization) ---
    # readonly_fields prevents staff from manually changing totals or order numbers
    readonly_fields = [
        'order_number', 'user', 'customer_email', 'subtotal', 
        'tax', 'shipping', 'total', 'created_at', 'updated_at'
    ]

    fieldsets = (
        ('Reference Info', {
            'fields': ('order_number', 'created_at')
        }),
        ('Status & Logistics', {
            'fields': (
                ('status', 'payment_status'), 
                'tracking_number', 
                ('shipped_at', 'delivered_at'),
                'notes'
            )
        }),
        ('Customer Details', {
            'fields': (
                'user', 'customer_email', 'customer_phone', 
                'shipping_address', 'billing_address'
            )
        }),
        ('Payment & Financials', {
            'fields': (
                'payment_method', 'transaction_id', 
                'subtotal', 'tax', 'shipping', 'discount_amount', 'total'
            )
        }),
    )

    inlines = [OrderItemInline, OrderStatusHistoryInline]

    # --- 5. Custom Admin Actions ---
    actions = ['mark_as_confirmed', 'mark_as_shipped', 'mark_as_delivered']

    def mark_as_confirmed(self, request, queryset):
        queryset.update(status=Order.Status.CONFIRMED)
    mark_as_confirmed.short_description = "✅ Mark selected as Confirmed"

    def mark_as_shipped(self, request, queryset):
        queryset.update(status=Order.Status.SHIPPED)
    mark_as_shipped.short_description = "🚚 Mark selected as Shipped"

    # --- 6. Aesthetic Helpers ---
    def user_link(self, obj):
        return obj.user.email
    user_link.short_description = 'Customer'

    def total_display(self, obj):
        return format_html('<b style="color: #4f46e5;">Rs: {}</b>', obj.total)
    total_display.short_description = 'Total'

    def status_badge(self, obj):
        colors = {
            'pending': '#f59e0b',   
            'confirmed': '#3b82f6',  
            'shipped': '#8b5cf6',    
            'delivered': '#10b981',  
            'cancelled': '#ef4444',  
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 12px; font-size: 10px; font-weight: bold; text-transform: uppercase;">{}</span>',
            colors.get(obj.status, '#64748b'),
            obj.status
        )
    status_badge.short_description = 'Order Status'

    def payment_status_badge(self, obj):
        is_paid = obj.payment_status == 'completed'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            '#10b981' if is_paid else '#ef4444',
            obj.get_payment_status_display()
        )
    payment_status_badge.short_description = 'Payment'

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['transaction_id', 'order', 'amount', 'status', 'created_at']
    readonly_fields = ['transaction_id', 'order', 'amount', 'currency', 'provider_response']