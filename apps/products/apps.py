from django.apps import AppConfig
import sys

class ProductsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.products'

    def ready(self):
        # Prevent training during migrations or management commands
        if 'runserver' in sys.argv:
            from .recommender import recommender_engine
            recommender_engine.train()