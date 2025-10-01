# restaurants/views.py
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
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
    reviews_qs = Review.objects.filter(restaurant=restaurant).select_related('user').order_by('-created_at')
    paginator = Paginator(reviews_qs, 10)  # 10 reviews per page
    page_number = request.GET.get('page')
    try:
        reviews = paginator.page(page_number)
    except PageNotAnInteger:
        reviews = paginator.page(1)
    except EmptyPage:
        reviews = paginator.page(paginator.num_pages)

    #Window nomor halaman untuk template
    current_page = reviews.number
    last_page = paginator.num_pages
    start = max(current_page - 2, 1)
    end = min(current_page + 2, last_page) + 1
    page_range = range(start, end)

    # Cek apakah user sudah bookmark
    is_bookmarked = False
    if request.user.is_authenticated:
        from accounts.models import Bookmark
        is_bookmarked = Bookmark.objects.filter(user=request.user, restaurant=restaurant).exists()

    # Data restoran untuk peta
    has_lat = restaurant.latitude is not None
    has_lng = restaurant.longitude is not None
    has_coordinate = (has_lat and has_lng)


    restaurant_data = {
        'id': restaurant.id,
        'name': str(restaurant.name),
        'address': str(restaurant.address),
        'lat': float(restaurant.latitude) if has_lat else None,
        'lng': float(restaurant.longitude) if has_lng else None,
    }

    context = {
        'restaurant': restaurant,
        'avg_rating': round(avg_rating, 1) if avg_rating else 0,
        'review_count': review_count,
        'menus': menus,
        'reviews': reviews,
        'is_bookmarked': is_bookmarked,
        'restaurant_data': restaurant_data,  # 👈 Tambah ini
        'has_coordinate': has_coordinate,
    }
    return render(request, 'restaurants/detail.html', context)