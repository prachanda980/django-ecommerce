from django.db import transaction
from django.core.exceptions import ValidationError
from .models import Cart, CartItem
from apps.products.models import Product

class CartService:
    @staticmethod
    def get_cart(user):
        """Get or create a cart for the user."""
        cart, created = Cart.objects.get_or_create(user=user, is_active=True)
        return cart

    @staticmethod
    @transaction.atomic
    def add_to_cart(user, product_id, quantity=1):
        """
        Add item to cart and safely reserve stock.
        """
        cart = CartService.get_cart(user)
        
        # 1. Lock the Product Row (Prevent Race Conditions)
        try:
            product = Product.objects.select_for_update().get(id=product_id)
        except Product.DoesNotExist:
            raise ValidationError("Product not found.")

        # 2. Check and Reserve Stock
        # (Assuming reserve_stock returns True if successful, defined in Product model)
        if not product.reserve_stock(quantity):
            raise ValidationError(f"Insufficient stock. Only {product.available_stock} remaining.")

        # 3. Create or Update Cart Item
        item, created = CartItem.objects.get_or_create(
            cart=cart, 
            product=product,
            defaults={'quantity': 0}
        )
        
        item.quantity += quantity
        item.save()
        
        return cart

    @staticmethod
    @transaction.atomic
    def update_quantity(user, product_id, new_quantity):
        """
        Update item quantity. Handles both stock increase (reserve) and decrease (release).
        """
        if new_quantity < 1:
            return CartService.remove_from_cart(user, product_id)

        cart = CartService.get_cart(user)
        
        # Lock product
        product = Product.objects.select_for_update().get(id=product_id)
        
        try:
            item = CartItem.objects.get(cart=cart, product=product)
        except CartItem.DoesNotExist:
            raise ValidationError("Item not in cart.")

        diff = new_quantity - item.quantity

        if diff > 0:
            # User wants MORE items -> Reserve more stock
            if not product.reserve_stock(diff):
                raise ValidationError("Insufficient stock for update.")
        elif diff < 0:
            # User wants FEWER items -> Release stock back to pool
            product.release_reserved_stock(abs(diff))

        item.quantity = new_quantity
        item.save()
        return cart

    @staticmethod
    @transaction.atomic
    def remove_from_cart(user, product_id):
        """
        Remove item and release held stock.
        """
        cart = CartService.get_cart(user)
        
        try:
            item = CartItem.objects.select_related('product').get(cart=cart, product_id=product_id)
        except CartItem.DoesNotExist:
            return cart

        # Release the reserved stock
        item.product.release_reserved_stock(item.quantity)
        
        item.delete()
        return cart

    @staticmethod
    @transaction.atomic
    def clear_cart(user):
        """
        Empty cart and release ALL reserved stock.
        """
        cart = CartService.get_cart(user)
        items = cart.items.select_related('product').all()
        
        for item in items:
            item.product.release_reserved_stock(item.quantity)
            
        items.delete()
        return cart