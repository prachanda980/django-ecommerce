from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .models import Product, Category
from .serializers import ProductSerializer, CategorySerializer
from .services import ProductCacheService

class ProductListAPIView(generics.ListAPIView):
    """
    GET /api/products/products/
    Returns a paginated list of active products.
    """
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        qs = Product.objects.filter(is_active=True).select_related('category').prefetch_related('images')
        
        # Filtering by Category
        category_slug = self.request.query_params.get('category')
        if category_slug:
            qs = qs.filter(category__slug=category_slug)
            
        return qs

class ProductDetailAPIView(generics.RetrieveAPIView):
    """
    GET /api/products/products/<id>/
    Returns a single product detail.
    """
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]

class CategoryListAPIView(generics.ListAPIView):
    """
    GET /api/products/categories/
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]

class TrendingProductsAPIView(APIView):
    """
    GET /api/products/trending/
    Returns top 10 products using the Cache Service.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        # 1. Get raw data from Redis/Service
        data = ProductCacheService.get_cached_trending_products()
        
        # 2. Return as JSON
        return Response(data)