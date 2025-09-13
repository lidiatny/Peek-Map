from django.contrib import admin
from .models import Bookmark
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

admin.site.unregister(User)
admin.site.register(User, UserAdmin)

@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ('user', 'restaurant', 'created_at')
    search_fields = ('user__username', 'restaurant__name')
    list_filter = ('created_at',)
    ordering = ('-created_at',)