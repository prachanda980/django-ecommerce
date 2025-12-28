import json
import logging
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.generic import ListView, DetailView
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.shortcuts import redirect, render
from django.contrib import messages
from .forms import ProductReviewForm
from django.db.models import Avg,Count
from .models import Product, Category
from .services import ProductCacheService
from .recommender import recommender_engine



logger = logging.getLogger(__name__)

# --- Standard UI Views ---
class ProductListView(ListView):
    model = Product
    template_name = 'home.html'
    context_object_name = 'products'
    # --- ADD PAGINATION HERE ---
    paginate_by = 10 

    def get_queryset(self):
        # Optimized query with prefetching
        qs = Product.objects.filter(is_active=True).prefetch_related('images').select_related('category')
        category_slug = self.kwargs.get('category_slug')
        if category_slug:
            qs = qs.filter(category__slug=category_slug)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # --- TOP RATED LOGIC ---
        context['top_rated'] = Product.objects.annotate(
            avg_rating=Avg('reviews__rating'),
            review_count=Count('reviews')
        ).filter(avg_rating__isnull=False).order_by('-avg_rating', '-review_count').first()
        
        context['categories'] = Category.objects.all()
        
        category_slug = self.kwargs.get('category_slug')
        if category_slug:
            # Using filter().first() to avoid exception if slug is wrong
            context['current_category'] = Category.objects.filter(slug=category_slug).first()
            
        return context

class ProductDetailView(DetailView):
    model = Product
    template_name = 'products/product_detail.html'
    context_object_name = 'product'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object

        # Fetch IDs directly from the local engine
        rec_ids = recommender_engine.get_recommendations(product.id)
        
        # Get full objects for the template
        context['recommendations'] = Product.objects.filter(
            id__in=rec_ids, 
            is_active=True
        ).prefetch_related('images')[:4]

        return context
@require_http_methods(["GET"])
def check_stock(request, product_id):
    """
    Simple API to check stock count.
    """
    try:
        qty = int(request.GET.get('quantity', 1))
        is_avail, stock = ProductCacheService.check_real_time_stock(product_id, qty)
        
        return JsonResponse({
            'product_id': product_id,
            'available': is_avail,
            'current_stock': stock,
            'timestamp': timezone.now().isoformat()
        })
    except ValueError:
        return JsonResponse({'error': 'Invalid quantity'}, status=400)


# FIX: Added the Missing Function Here
@require_http_methods(["GET"])
def get_product_detail_api(request, product_id):
    """
    Internal API used by Frontend JS to fetch product details + REAL-TIME stock
    without a full page refresh.
    """
    try:
        # 1. Get Static Data from Cache (Fast)
        product_data = ProductCacheService.get_cached_product_detail(product_id)
        
        if not product_data:
            return JsonResponse({
                'status': 'error',
                'message': 'Product not found in cache'
            }, status=404)
        
        # 2. Get Dynamic Stock from DB (Accurate & Locked if needed)
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Product not found in DB'
            }, status=404)
        
        # 3. Merge real-time stock into the cached metadata
        product_data['stock'] = product.stock
        product_data['available_stock'] = product.available_stock
        product_data['is_in_stock'] = product.is_in_stock
        product_data['reserved_stock'] = product.reserved_stock
        
        return JsonResponse({
            'status': 'success',
            'product': product_data
        })
        
    except Exception as e:
        logger.error(f"Error getting product detail API: {e}")
        return JsonResponse({
            'status': 'error',
            'message': 'Server Error'
        }, status=500)


@csrf_exempt
@require_POST
@login_required
def process_purchase(request):
    """
    API: Handle Checkout via JSON.
    """
    from apps.orders.services import OrderService 

    try:
        data = json.loads(request.body)
        items = data.get('items', [])
        
        if not items:
            return JsonResponse({'status': 'error', 'message': 'Cart is empty'}, status=400)

        result = OrderService.create_order(
            user=request.user,
            items=items,
            shipping_address=data.get('shipping_address'),
            billing_address=data.get('billing_address'),
            payment_method=data.get('payment_method', 'credit_card')
        )

        if result.get('status') == 'success':
            return JsonResponse(result, status=201)
        else:
            return JsonResponse(result, status=400)

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Purchase Error: {str(e)}")
        return JsonResponse({'status': 'error', 'message': 'Server Error'}, status=500)
    

# Handle Review Submission
@login_required
@require_http_methods(["POST"])
def submit_review(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    
    if product.reviews.filter(user=request.user).exists():
        messages.error(request, "You have already reviewed this product.")
        return redirect('products:detail', slug=slug)

    form = ProductReviewForm(request.POST, user=request.user, product=product)
    if form.is_valid():
        review = form.save(commit=False)
        review.product = product
        review.user = request.user
        review.save()
        messages.success(request, "Thank you! Your review has been submitted and is awaiting approval.")
    else:
        messages.error(request, "Please correct the errors below.")
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, error)

    return redirect('products:detail', slug=slug)

def top_rated_product(request):
    # 1. Annotate each product with its average rating
    # 2. Order by average_rating descending
    # 3. Get the first one
    top_product = Product.objects.annotate(
        avg_rating=Avg('reviews__rating') # 'reviews' is the related_name in your Review model
    ).filter(avg_rating__isnull=False).order_by('-avg_rating').first()

    context = {
        'product': top_product
    }
    return render(request, 'products/top_rated.html', context)