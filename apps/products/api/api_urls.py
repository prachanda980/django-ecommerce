from django.urls import path
from . import api_views

# Namespace is defined in the main urls.py, usually 'products_api'

urlpatterns = [
    # Product Endpoints
    path('products/', api_views.ProductListAPIView.as_view(), name='list'),
    path('products/<int:pk>/', api_views.ProductDetailAPIView.as_view(), name='detail'),
    
    # Category Endpoints
    path('categories/', api_views.CategoryListAPIView.as_view(), name='categories'),
    
    # Special Endpoints
    path('trending/', api_views.TrendingProductsAPIView.as_view(), name='trending'),
]