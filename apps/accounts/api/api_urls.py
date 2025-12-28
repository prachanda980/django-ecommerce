from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .api_views import RegisterAPIView, ProfileAPIView, CustomTokenObtainPairView

urlpatterns = [
    # Auth
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('login/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('register/', RegisterAPIView.as_view(), name='auth_register'),
    
    # Profile
    path('profile/', ProfileAPIView.as_view(), name='auth_profile'),
]