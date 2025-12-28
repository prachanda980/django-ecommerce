from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from .models import Order
from .serializers import OrderSerializer
from .services import OrderService

class OrderListAPIView(generics.ListAPIView):
    """
    GET /api/orders/
    List all orders belonging to the authenticated user.
    """
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Filter strictly by the logged-in user
        return Order.objects.filter(user=self.request.user)

class OrderDetailAPIView(generics.RetrieveAPIView):
    """
    GET /api/orders/<id>/
    Get details of a specific order.
    """
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'order_number' # Use order_number (ORD...) instead of ID for security

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

class CancelOrderAPIView(APIView):
    """
    POST /api/orders/<id>/cancel/
    Attempts to cancel the order via the Service layer.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, order_id):
        result = OrderService.cancel_order(
            order_id=order_id,
            user=request.user,
            reason=request.data.get('reason', 'Cancelled via API')
        )
        
        if result['status'] == 'success':
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_400_BAD_REQUEST)