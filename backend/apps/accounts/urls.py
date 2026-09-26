from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    AdminUserBulkDeleteView,
    AdminUserListView,
    AdminUserResetPasswordView,
    AdminUserUpdateView,
    LoginView,
    LogoutView,
    MeView,
    MyEmailView,
    RegisterView,
    SuperAdminEmailDetailView,
    SuperAdminEmailListView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("token/", LoginView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("me/", MeView.as_view(), name="me"),
    path("admin/users/", AdminUserListView.as_view(), name="admin_user_list"),
    path("admin/super-emails/", SuperAdminEmailListView.as_view(),
         name="admin_super_email_list"),
    path("admin/super-emails/<int:pk>/", SuperAdminEmailDetailView.as_view(),
         name="admin_super_email_detail"),
    path("me/email/", MyEmailView.as_view(), name="my_email"),
    path("admin/users/bulk-delete/", AdminUserBulkDeleteView.as_view(),
         name="admin_user_bulk_delete"),
    path("admin/users/<int:pk>/reset-password/", AdminUserResetPasswordView.as_view(),
         name="admin_user_reset_password"),
    path("admin/users/<int:pk>/", AdminUserUpdateView.as_view(), name="admin_user_update"),
]