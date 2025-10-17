from django.contrib import admin
from .models import Restaurant, Menu

@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'address', 'latitude', 'longitude', 'average_rating')
    search_fields = ('name', 'address')
    list_filter = ('created_at',)
    ordering = ('-created_at',)

    # Field khusus untuk average_rating (hanya baca)
    readonly_fields = ('average_rating',)

    def average_rating(self, obj):
        return f"{obj.average_rating} ⭐"
    average_rating.short_description = 'Rating Rata-rata'


@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    list_display = ('name', 'restaurant', 'price', 'formatted_price')
    search_fields = ('name', 'restaurant__name')
    list_filter = ('restaurant',)
    ordering = ('restaurant', 'name')

    def formatted_price(self, obj):
        return f"Rp {obj.price:,.0f}"
    formatted_price.short_description = 'Harga'