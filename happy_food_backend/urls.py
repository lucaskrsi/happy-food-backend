from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from food.view_auth import CustomTokenObtainPairView
from food.view_logout import LogoutView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("food.urls")),  # 👈 integra as rotas da API
    path("auth/token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("api/logout/", LogoutView.as_view(), name="auth_logout"),
]
