from django.urls import path
from . import api_views

app_name = 'cart_api'

urlpatterns = [
    path('', api_views.CartAPIView.as_view(), name='detail'),
    path('items/', api_views.CartItemAPIView.as_view(), name='add_item'),
    path('items/<int:product_id>/', api_views.CartItemAPIView.as_view(), name='item_detail'),
]