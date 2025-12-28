from django.shortcuts import render
def custom_page_not_found_view(request, exception):
    return render(request, 'errors/404.html', status=404)

def custom_error_view(request, *args, **argv):
    return render(request, 'errors/500.html', status=500)

def custom_permission_denied_view(request, exception):
    return render(request, 'errors/403.html', status=403)

def custom_bad_request_view(request, exception):
    return render(request, 'errors/400.html', status=400)