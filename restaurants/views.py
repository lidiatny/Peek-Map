# restaurants/views.py
from django.shortcuts import render, get_object_or_404
from django.db.models import Avg, Count
from restaurants.models import Restaurant, Menu
from reviews.models import Review
from core.utils import track_user_activity

def restaurant_detail(request, restaurant_id):
    # Ambil restoran atau 404
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    
    # Track restaurant view activity
    track_user_activity(request.user, 'view', restaurant=restaurant)

    # Anotasi rating rata-rata dan jumlah review
    avg_rating = Review.objects.filter(restaurant=restaurant).aggregate(Avg('rating'))['rating__avg']
    review_count = Review.objects.filter(restaurant=restaurant).count()

    # Daftar menu di restoran ini
    menus = Menu.objects.filter(restaurant=restaurant)

    # Daftar review
    reviews = Review.objects.filter(restaurant=restaurant).select_related('user').order_by('-created_at')

    # Cek apakah user sudah bookmark
    is_bookmarked = False
    if request.user.is_authenticated:
        from accounts.models import Bookmark
        is_bookmarked = Bookmark.objects.filter(user=request.user, restaurant=restaurant).exists()

    restaurant_data = {
    'name': str(restaurant.name),
    'address': str(restaurant.address),
    'lat': float(restaurant.latitude),
    'lng': float(restaurant.longitude),
    }

    context = {
        'restaurant': restaurant,
        'avg_rating': round(avg_rating, 1) if avg_rating else 0,
        'review_count': review_count,
        'menus': menus,
        'reviews': reviews,
        'is_bookmarked': is_bookmarked,
        'restaurant_data': restaurant_data,  # 👈 Tambah ini
    }
    return render(request, 'restaurants/detail.html', context)