# apps/products/urls.py
from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    path('', views.ProductListView.as_view(), name='list'),
    path('category/<slug:category_slug>/', views.ProductListView.as_view(), name='category_list'),
    path('product/<slug:slug>/', views.ProductDetailView.as_view(), name='detail'),
    
    # New: Submit Review
    path('product/<slug:slug>/review/', views.submit_review, name='submit_review'),
    path('top-rated/', views.top_rated_product, name='top_rated'),
]