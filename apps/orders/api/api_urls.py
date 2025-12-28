from django.urls import path
from . import api_views

app_name = 'orders_api'

urlpatterns = [
    # JSON: List all orders
    path('', api_views.OrderListAPIView.as_view(), name='list'),
    
    # JSON: Order Details
    path('<str:order_number>/', api_views.OrderDetailAPIView.as_view(), name='detail'),
    
    # JSON: Cancel Order
    path('<int:order_id>/cancel/', api_views.CancelOrderAPIView.as_view(), name='cancel'),
]