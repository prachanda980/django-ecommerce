import os
from django.core.asgi import get_asgi_application

# 1. Set the settings module first
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_ecommerce.settings')

# 2. Initialize Django. This must happen BEFORE importing any project code.
# This function calls django.setup() internally.
django_asgi_app = get_asgi_application()

# 3. NOW it is safe to import your consumers and routing
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from apps.products.routing import websocket_urlpatterns

# 4. Define the application
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})