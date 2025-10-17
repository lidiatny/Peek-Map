from django.contrib import admin
from .models import Bookmark
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.admin.sites import NotRegistered  # for safety

User = get_user_model()

# Unregister bawaan (aman kalau belum terdaftar)
try:
    admin.site.unregister(User)
except NotRegistered:
    pass

@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    # tambahkan kolom id supaya kelihatan
    list_display = ('id', 'username', 'email', 'first_name', 'last_name', 'is_staff')
    # opsional: bisa juga tambahkan pencarian & filter
    search_fields = ('id', 'username', 'email', 'first_name', 'last_name')

@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ('user', 'restaurant', 'created_at')
    search_fields = ('user__username', 'restaurant__name')
    list_filter = ('created_at',)
    ordering = ('-created_at',)

