from django.contrib import admin

from .models import RecruiterProfile, StudentProfile, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "role", "is_staff", "is_superuser")
    list_filter = ("role", "is_staff", "is_superuser", "is_active")


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "full_name", "college", "branch", "graduation_year", "cgpa")


@admin.register(RecruiterProfile)
class RecruiterProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "company_name", "location")