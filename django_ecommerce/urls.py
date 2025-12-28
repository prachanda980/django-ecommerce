from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('adminsite/', admin.site.urls),
    
    path('', include('apps.products.urls')),
    path('cart/', include('apps.cart.urls')),
    path('orders/', include('apps.orders.urls')),
    path('accounts/', include('apps.accounts.urls')),

    # --- API URLs ---
    # FIX: Changed 'apps.products.api_urls' to 'apps.products.api.urls'
    # path('api/v1/products/', include('apps.products.api.urls')),

    # # Accounts API
    # path('api/v1/accounts/', include('apps.accounts.api_urls')),
    
    # # Orders API
    # path('api/v1/orders/', include('apps.orders.api_urls')),
    
    # # Cart API (Adding this to ensure Cart API works)
    # path('api/v1/cart/', include('apps.cart.api_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

handler404 = 'django_ecommerce.views.custom_page_not_found_view'
handler500 = 'django_ecommerce.views.custom_error_view'
handler403 = 'django_ecommerce.views.custom_permission_denied_view'
handler400 = 'django_ecommerce.views.custom_bad_request_view'