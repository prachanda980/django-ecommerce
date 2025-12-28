# accounts/views.py (or wherever admin_dashboard is)

from django.shortcuts import render
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import get_user_model
from apps.orders.models import Order 
from apps.products.models import Product

User = get_user_model()

def is_admin(user):
    return user.is_authenticated and user.is_staff

@user_passes_test(is_admin, login_url='/accounts/login/')
def admin_dashboard(request):
    total_users = User.objects.count()
    total_products = Product.objects.count()
    total_orders = Order.objects.count()
    
    total_revenue = Order.objects.aggregate(
        sum_total=Sum('total')
    )['sum_total'] or 0

    monthly_sales = (
        Order.objects
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(total_sales=Sum('total'))
        .order_by('month')
    )

 
    labels = [entry['month'].strftime('%b %Y') for entry in monthly_sales]
    
    data = [float(entry['total_sales']) for entry in monthly_sales]

    context = {
        'total_users': total_users,
        'total_products': total_products,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'chart_labels': labels,
        'chart_data': data,
    }

    return render(request, 'admin/admin_dashboard.html', context)