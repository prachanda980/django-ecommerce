import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages

from .models import Order
from .forms import CheckoutForm
from .services import OrderService
from apps.cart.services import CartService

logger = logging.getLogger(__name__)

class OrderListView(LoginRequiredMixin, ListView):
    """
    Displays the logged-in user's order history.
    """
    model = Order
    template_name = 'orders/order_list.html'
    context_object_name = 'orders'
    paginate_by = 10

    def get_queryset(self):
        # Only show orders belonging to the user
        return Order.objects.filter(user=self.request.user).order_by('-created_at')


class OrderDetailView(LoginRequiredMixin, DetailView):
    """
    Displays detailed digital receipt for a specific order.
    """
    model = Order
    template_name = 'orders/order_detail.html'
    context_object_name = 'order'
    slug_field = 'order_number'
    slug_url_kwarg = 'order_number'

    def get_queryset(self):
        # Security: Filter by user and prefetch items + product images for the UI
        return Order.objects.filter(user=self.request.user).prefetch_related(
            'items__product__images'
        )


class CheckoutView(LoginRequiredMixin, View):
    """
    Handles the Checkout process.
    - Logic for 'Hands on Cash' (COD) is processed in the OrderService.
    - Ensures data integrity and stock locking.
    """
    template_name = 'orders/checkout.html'

    def get(self, request):
        cart = CartService.get_cart(request.user)
        
        if cart.item_count == 0:
            messages.warning(request, "Your cart is empty.")
            return redirect('cart:detail')

        # Provide initial data like user's phone if it exists in their profile
        form = CheckoutForm(initial={
            'customer_phone': getattr(request.user, 'phone', ''),
        })

        context = {
            'form': form,
            'cart': cart,
            'items': cart.items.select_related('product').prefetch_related('product__images').all(),
            'total': cart.total_price,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        cart = CartService.get_cart(request.user)

        if cart.item_count == 0:
            messages.error(request, "Your cart is empty.")
            return redirect('products:list')

        form = CheckoutForm(request.POST)

        if form.is_valid():
            # Cleaned data includes: shipping_address, billing_address, customer_phone, payment_method
            user_data = form.cleaned_data

            # Prepare product data for the atomic Service Layer
            items_data = [
                {'product_id': item.product.id, 'quantity': item.quantity}
                for item in cart.items.all()
            ]

            # Trigger the transactional OrderService
            result = OrderService.create_order(
                user=request.user,
                items=items_data,
                **user_data
            )

            if result['status'] == 'success':
                # Critical: Only clear cart if order creation succeeded
                CartService.clear_cart(request.user)
                
                messages.success(
                    request,
                    f"Order #{result['order_number']} placed successfully! Check your email for details."
                )
                return redirect('orders:detail', order_number=result['order_number'])
            
            else:
                # Handle Service-level errors (e.g., Database lock timeout or Stock issues)
                messages.error(request, result.get('message', "Order processing failed."))
                if 'details' in result:
                    for detail in result['details']:
                        messages.error(request, f"{detail['product']}: Requested {detail['requested']}, but only {detail['available']} available.")

        else:
            # Handle Form-level validation errors (e.g., missing phone or invalid characters)
            for field, errors in form.errors.items():
                for error in errors:
                    # Format field names (e.g., 'customer_phone' -> 'Customer Phone')
                    field_name = field.replace('_', ' ').title()
                    messages.error(request, f"{field_name}: {error}")

        # If we reach here, re-render with the form errors and preserved data
        context = {
            'form': form,
            'cart': cart,
            'items': cart.items.select_related('product').prefetch_related('product__images').all(),
            'total': cart.total_price,
        }
        return render(request, self.template_name, context)


class CancelOrderView(LoginRequiredMixin, View):
    # 🟢 Change 'pk' to 'order_id' to match your URL pattern
    def post(self, request, order_id): 
        
        result = OrderService.cancel_order(
            order_id=order_id,
            user=request.user,
            reason="Cancelled by customer via dashboard."
        )
        
        if result['status'] == 'success':
            messages.success(request, result['message'])
            # We use 'order_id' here too to look up the order number for redirect
            order = request.user.orders.get(pk=order_id)
            return redirect('orders:detail', order_number=order.order_number)
        else:
            messages.error(request, result.get('message', "Unable to cancel order."))
            return redirect('orders:list')