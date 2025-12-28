from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    # 1. History: /orders/
    path('', views.OrderListView.as_view(), name='list'),
    
    # 2. Process: /orders/checkout/
    path('checkout/', views.CheckoutView.as_view(), name='checkout'),
    
    # 3. Receipt: /orders/ORD20251228.../
    # We put this after 'checkout' so 'checkout' isn't mistaken for an order number
    path('<str:order_number>/', views.OrderDetailView.as_view(), name='detail'),
    
    # 4. Action: /orders/5/cancel/
    path('<int:order_id>/cancel/', views.CancelOrderView.as_view(), name='cancel'),
]