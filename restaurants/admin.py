from django.contrib import admin
from .models import Restaurant, Menu
from django.utils.formats import number_format

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
    list_display = ("id", "restaurant", "name", "formatted_price")
    search_fields = ("name", "restaurant__name")

    @admin.display(description="Price", ordering="price")
    def formatted_price(self, obj):
        if obj.price is None:
            return "-"  # atau "N/A"
        # aman untuk Decimal, dan pakai pemisah Indonesia
        return f"Rp {number_format(obj.price, 0, decimal_sep=',', thousand_sep='.', force_grouping=True)}"