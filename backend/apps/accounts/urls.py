from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    AdminUserListView,
    AdminUserUpdateView,
    MeView,
    RegisterView,
    TokenObtainPairWithRoleView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("token/", TokenObtainPairWithRoleView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("me/", MeView.as_view(), name="me"),
    path("admin/users/", AdminUserListView.as_view(), name="admin_user_list"),
    path("admin/users/<int:pk>/", AdminUserUpdateView.as_view(), name="admin_user_update"),
]