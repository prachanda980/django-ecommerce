from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.core.exceptions import ValidationError

from .services import CartService

@login_required
def cart_detail(request):
    """
    Renders the cart page (HTML).
    Template: cart/cart_detail.html
    """
    cart = CartService.get_cart(request.user)
    context = {
        'cart': cart,
        'items': cart.items.select_related('product').all()
    }
    return render(request, 'cart/cart_detail.html', context)

@login_required
@require_POST
def add_to_cart(request, product_id):
    """
    Handle 'Add to Cart' form submission from Product Page.
    """
    quantity = int(request.POST.get('quantity', 1))
    
    try:
        CartService.add_to_cart(request.user, product_id, quantity)
        messages.success(request, "Item added to cart.")
    except ValidationError as e:
        messages.error(request, str(e))
    except Exception:
        messages.error(request, "Could not add item.")

    # Redirect back to where the user came from, or the cart
    return redirect(request.META.get('HTTP_REFERER', 'cart:detail'))

@login_required
@require_POST
def update_cart_item(request, product_id):
    """
    Handle quantity updates from the Cart Page.
    """
    quantity = int(request.POST.get('quantity', 1))
    
    try:
        CartService.update_quantity(request.user, product_id, quantity)
        messages.success(request, "Cart updated.")
    except ValidationError as e:
        messages.error(request, str(e))
        
    return redirect('cart:detail')

@login_required
@require_POST
def remove_cart_item(request, product_id):
    """
    Handle 'Remove' button click.
    """
    CartService.remove_from_cart(request.user, product_id)
    messages.success(request, "Item removed.")
    return redirect('cart:detail')
