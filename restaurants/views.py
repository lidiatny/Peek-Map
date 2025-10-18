# restaurants/views.py
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Avg, Count
from restaurants.models import Restaurant, Menu
from reviews.models import Review
from django.db.models import Count
from core.utils import track_user_activity

def restaurant_detail(request, restaurant_id):
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)

    # Track view (hanya kalau login)
    if request.user.is_authenticated:
        track_user_activity(request.user, 'view', restaurant=restaurant)

    # Aggregate rating & jumlah review
    agg = Review.objects.filter(restaurant=restaurant).aggregate(
        avg_rating=Avg('rating'),
        total=Count('id'),
    )

    breakdown_qs = (
    Review.objects
    .filter(restaurant=restaurant)
    .values('rating')
    .annotate(total=Count('id'))
    )

    # siapkan count per bintang 5..1
    rating_counts = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    for row in breakdown_qs:
        r = int(row['rating'] or 0)
        if r in rating_counts:
            rating_counts[r] = row['total']

    rating_total = sum(rating_counts.values()) or 1  # hindari bagi 0
    rating_percents = {
        k: int(v * 100 / rating_total) for k, v in rating_counts.items()
    }

    context = {
    # …yang sudah ada
    'rating_counts': rating_counts,
    'rating_percents': rating_percents,
    }

    avg_rating_raw = agg['avg_rating']
    review_count = agg['total'] or 0
    avg_rating = round(avg_rating_raw, 1) if avg_rating_raw is not None else 0

    # Menu tanpa category
    menus = Menu.objects.filter(restaurant=restaurant).order_by('name')

    # Reviews + pagination
    reviews_qs = (
        Review.objects
        .filter(restaurant=restaurant)
        .select_related('user')
        .order_by('-created_at')
    )
    paginator = Paginator(reviews_qs, 10)
    page_number = request.GET.get('page')

    if paginator.count == 0:
        reviews = None
        page_range = range(0)
    else:
        try:
            reviews = paginator.page(page_number)
        except PageNotAnInteger:
            reviews = paginator.page(1)
        except EmptyPage:
            reviews = paginator.page(paginator.num_pages)

        current_page = reviews.number
        last_page = paginator.num_pages
        start = max(current_page - 2, 1)
        end = min(current_page + 2, last_page) + 1
        page_range = range(start, end)

    # Bookmark?
    is_bookmarked = False
    if request.user.is_authenticated:
        from accounts.models import Bookmark
        is_bookmarked = Bookmark.objects.filter(
            user=request.user, restaurant=restaurant
        ).exists()

    # Data peta
    has_lat = restaurant.latitude is not None
    has_lng = restaurant.longitude is not None
    has_coordinate = has_lat and has_lng
    restaurant_data = {
        'id': restaurant.id,
        'name': str(restaurant.name),
        'address': str(restaurant.address),
        'lat': float(restaurant.latitude) if has_lat else None,
        'lng': float(restaurant.longitude) if has_lng else None,
    }

    context = {
        'restaurant': restaurant,
        'avg_rating': avg_rating,
        'review_count': review_count,
        'menus': menus,
        'reviews': reviews,          # bisa None kalau belum ada review
        'page_range': page_range,    # <-- tambahin ke context
        'is_bookmarked': is_bookmarked,
        'restaurant_data': restaurant_data,
        'has_coordinate': has_coordinate,
    }
    return render(request, 'restaurants/detail.html', context)
