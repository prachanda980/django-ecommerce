import csv
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from apps.products.models import Product, Category, ProductReview
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Import products from the recommendation dataset'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str)

    def handle(self, *args, **options):
        path = options['csv_file']
        
        # FIX: Use email instead of username
        admin_user, _ = User.objects.get_or_create(
            email='admin@example.com', 
            defaults={'first_name': 'Admin', 'is_staff': True}
        )

        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 1. Create/Get Category
                # Note: Match the column name exactly as it appears in your CSV
                cat_name = row.get('Category', 'General') 
                category, _ = Category.objects.get_or_create(
                    name=cat_name, 
                    defaults={'slug': slugify(cat_name)}
                )

                # 2. Create/Get Product
                p_name = row.get('Product Name', 'Unknown Product')
                # Use SKU from CSV if available, otherwise generate one
                sku_val = row.get('SKU', slugify(p_name)[:10] + row.get('Price', '0'))

                product, created = Product.objects.get_or_create(
                    sku=sku_val,
                    defaults={
                        'name': p_name,
                        'slug': slugify(p_name + "-" + sku_val),
                        'description': f"Brand: {row.get('Brand')}. Description: {row.get('Description', 'No description available.')}",
                        'category': category,
                        'price': row.get('Price', 0.0),
                        'stock': 100,
                        'is_active': True
                    }
                )

                # 3. Handle Ratings (ML Feature 6)
                rating_val = row.get('Rating')
                if rating_val:
                    try:
                        ProductReview.objects.get_or_create(
                            product=product,
                            user=admin_user,
                            defaults={
                                'rating': int(float(rating_val)),
                                'comment': f"Sentiment: {row.get('Sentiment Score', 'N/A')}",
                                'is_approved': True
                            }
                        )
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"Could not add review for {p_name}: {e}"))

                if created:
                    self.stdout.write(self.style.SUCCESS(f"Successfully imported: {p_name}"))

        self.stdout.write(self.style.SUCCESS('--- Data Import Complete ---'))