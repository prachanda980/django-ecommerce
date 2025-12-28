from django.urls import path
from . import views

app_name = 'cart'

urlpatterns = [
    # Page: View Cart
    path('', views.cart_detail, name='detail'),
    
    # Action: Add Item (Form POST)
    path('add/<int:product_id>/', views.add_to_cart, name='add'),
    
    # Action: Update Quantity (Form POST)
    path('update/<int:product_id>/', views.update_cart_item, name='update'),
    
    # Action: Remove Item (Form POST)
    path('remove/<int:product_id>/', views.remove_cart_item, name='remove'),
]