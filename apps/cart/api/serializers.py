from rest_framework import serializers
from .models import Cart, CartItem
from apps.products.serializers import ProductSerializer 

class CartItemSerializer(serializers.ModelSerializer):
    # Nested serializer to show full product details
    product = ProductSerializer(read_only=True)
    # Write-only field for inputting product ID
    product_id = serializers.IntegerField(write_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_id', 'quantity', 'subtotal']

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    item_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Cart
        fields = ['id', 'user', 'items', 'total_price', 'item_count', 'updated_at']