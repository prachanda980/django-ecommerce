from django.apps import AppConfig

class OrdersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.orders'
    
    def ready(self):
        # Import signals if you have any (e.g., creating a Profile on User creation)
        pass