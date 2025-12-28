from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.core.exceptions import ValidationError

from .services import CartService
from .serializers import CartSerializer

class CartAPIView(APIView):
    """
    GET: View your cart.
    DELETE: Empty your cart.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart = CartService.get_cart(request.user)
        serializer = CartSerializer(cart)
        return Response(serializer.data)

    def delete(self, request):
        CartService.clear_cart(request.user)
        return Response({"message": "Cart cleared successfully"}, status=status.HTTP_200_OK)

class CartItemAPIView(APIView):
    """
    POST: Add item.
    PUT: Update quantity.
    DELETE: Remove item.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity', 1))

        if not product_id:
            return Response({"error": "Product ID required"}, status=400)

        try:
            cart = CartService.add_to_cart(request.user, product_id, quantity)
            return Response(CartSerializer(cart).data, status=201)
        except ValidationError as e:
            return Response({"error": str(e)}, status=400)
        except Exception:
            return Response({"error": "Failed to add item"}, status=500)

    def put(self, request, product_id):
        """Expects URL like /api/cart/items/1/ with body {"quantity": 5}"""
        quantity = request.data.get('quantity')
        
        if quantity is None:
            return Response({"error": "Quantity required"}, status=400)
            
        try:
            cart = CartService.update_quantity(request.user, product_id, int(quantity))
            return Response(CartSerializer(cart).data)
        except ValidationError as e:
            return Response({"error": str(e)}, status=400)

    def delete(self, request, product_id):
        """Expects URL like /api/cart/items/1/"""
        cart = CartService.remove_from_cart(request.user, product_id)
        return Response(CartSerializer(cart).data)