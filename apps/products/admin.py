from django.contrib import admin
from .models import Product, Category, ProductImage,ProductReview

class ProductImageInline(admin.TabularInline):
    """
    Allows adding multiple images directly inside the Product add/edit page.
    """
    model = ProductImage
    extra = 1  # Number of empty slots to show by default

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    # Columns to show in the list view
    list_display = ['name', 'price', 'stock', 'is_active', 'is_featured', 'category', 'updated_at']
    
    # Enable filtering by these fields on the right sidebar
    list_filter = ['is_active', 'is_featured', 'category', 'created_at']
    
    # Enable search bar (searches name and SKU)
    search_fields = ['name', 'description', 'sku']
    
    # Automatically generate slug from name when adding a product
    prepopulated_fields = {'slug': ('name',)}
    
    # Allow editing these fields directly in the list view (Quick Edit)
    list_editable = ['price', 'stock', 'is_active', 'is_featured']
    
    # Add the images section to the product page
    inlines = [ProductImageInline]
    
    # Organizing the form layout
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'category', 'description')
        }),
        ('Pricing & Inventory', {
            'fields': ('price', 'sku', 'stock', 'is_active', 'is_featured')
        }),
    )

# Add this at the bottom
@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating', 'is_approved', 'created_at']
    list_filter = ['is_approved', 'rating', 'created_at']
    search_fields = ['user__username', 'product__name', 'comment']
    readonly_fields = ['user', 'product', 'rating', 'comment', 'created_at']
    actions = ['approve_reviews']

    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)
        self.message_user(request, "Selected reviews have been approved.")
    approve_reviews.short_description = "Approve selected reviews"