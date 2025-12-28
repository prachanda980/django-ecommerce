from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/products/(?P<product_id>\w+)/$', consumers.ProductConsumer.as_asgi()),
]