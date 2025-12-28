import random
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.contrib.auth import get_user_model
from django.db import transaction
from faker import Faker
from apps.products.models import Category, Product, ProductReview

User = get_user_model()
fake = Faker()

class Command(BaseCommand):
    help = 'Seeds the database with 1000 random products using bulk_create'

    def handle(self, *args, **options):
        self.stdout.write("🚀 Starting high-volume seeding...")

        # 1. Setup Admin User
        admin_user, _ = User.objects.get_or_create(
            email='admin@example.com',
            defaults={'first_name': 'Admin', 'is_staff': True, 'is_superuser': True}
        )

        # 2. Setup Categories
        categories_names = ['Electronics', 'Fashion', 'Home', 'Books', 'Toys', 'Sports', 'Beauty', 'Automotive']
        categories = []
        for name in categories_names:
            cat, _ = Category.objects.get_or_create(
                name=name, 
                defaults={'slug': slugify(name), 'description': fake.sentence()}
            )
            categories.append(cat)

        # 3. Bulk Create Products (The Fast Way)
        products_to_create = []
        self.stdout.write("Generating 1000 products...")
        
        for i in range(1000):
            name = f"{fake.color_name()} {fake.word().capitalize()} {random.choice(['Pro', 'Max', 'Ultra', 'Lite', 'Plus'])}"
            sku = f"SKU-{random.randint(10000, 99999)}-{i}"
            
            products_to_create.append(Product(
                name=name,
                slug=slugify(f"{name}-{sku}"),
                description=fake.paragraph(nb_sentences=3),
                category=random.choice(categories),
                price=round(random.uniform(5.0, 999.0), 2),
                stock=random.randint(0, 500),
                sku=sku,
                is_active=True,
                is_featured=random.choice([True, False]),
                weight=round(random.uniform(0.5, 10.0), 2)
            ))

        # Perform the bulk insert
        Product.objects.bulk_create(products_to_create)
        self.stdout.write(self.style.SUCCESS("✅ 1000 Products inserted!"))

        # 4. Bulk Create Reviews
        # We fetch IDs of newly created products to link reviews
        product_ids = Product.objects.values_list('id', flat=True).order_by('-id')[:1000]
        reviews_to_create = []
        
        self.stdout.write("Generating random reviews...")
        for p_id in product_ids:
            for _ in range(random.randint(1, 3)):
                reviews_to_create.append(ProductReview(
                    product_id=p_id,
                    user=admin_user,
                    rating=random.randint(3, 5),
                    comment=fake.sentence(),
                    is_approved=True
                ))
        
        ProductReview.objects.bulk_create(reviews_to_create)
        self.stdout.write(self.style.SUCCESS("✅ Reviews inserted! Seeding complete."))