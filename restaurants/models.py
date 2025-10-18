from django.db import models

class Restaurant(models.Model):
    # === kolom lama ===
    name = models.CharField(max_length=100)             # map dari 'resto_name'
    address = models.TextField(blank=True, null=True)   # tidak ada di file? biarin optional
    latitude = models.FloatField(null=True, blank=True) # map dari 'latitude'
    longitude = models.FloatField(null=True, blank=True)# map dari 'longitude'
    rating = models.FloatField(null=True, blank=True)   # boleh diisi / biarkan dihitung dari reviews
    description = models.TextField(blank=True, null=True)
    photo = models.ImageField(upload_to='resto_photos/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # === kolom baru agar cocok dengan file ===
    # resto_id eksternal dari file; simpan terpisah supaya gak bentrok PK internal
    external_id = models.CharField(
        max_length=64, unique=True, null=True, blank=True, db_index=True,
        help_text="ID restoran dari file sumber (resto_id)"
    )
    # 'type' dari file = jenis masakan; pakai nama python-friendly tapi kolom DB tetap 'type'
    cuisine_type = models.CharField(
        max_length=100, null=True, blank=True, db_column='type'
    )
    city = models.CharField(max_length=100, null=True, blank=True)
    keywords = models.TextField(null=True, blank=True, help_text="Comma-separated keywords from file")
    price_range = models.CharField(max_length=50, null=True, blank=True)
    menu_list = models.TextField(null=True, blank=True, help_text="Raw 'list menu' string from file")  # simpan mentah dulu
    review_count = models.IntegerField(null=True, blank=True, default=0)

    def __str__(self):
        return self.name

    @property
    def average_rating(self):
        qs = self.review_set.all()
        if not qs.exists():
            return 0
        return round(sum(r.rating for r in qs if r.rating is not None) / qs.count(), 1)

    class Meta:
        db_table = 'restaurant'
        verbose_name = 'Restaurant'
        verbose_name_plural = 'Restaurants'


class Menu(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='menus')
    photo = models.ImageField(upload_to='menu_photos/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.restaurant.name})"

    class Meta:
        db_table = 'menu'
        verbose_name = 'Menu'
        verbose_name_plural = 'Menus'
