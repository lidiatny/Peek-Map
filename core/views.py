# core/views.py
from django.shortcuts import render
from django.db.models import Avg, Count
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from restaurants.models import Restaurant, Menu
from reviews.models import Review
from accounts.models import Bookmark

from .recommendations import simple_recommendation
from .utils import track_user_activity, get_recently_viewed_restaurants

def home(request):
    query = request.GET.get('q')
    category = request.GET.get('category')
    min_rating = request.GET.get('min_rating')
    
    # Initialize with all restaurants if any filter is applied
    if query or category or min_rating:
        if query:
            # Track search activity
            track_user_activity(request.user, 'search', search_query=query)
            resto_results = Restaurant.objects.filter(name__icontains=query)
            menu_results = Menu.objects.filter(name__icontains=query)
        else:
            resto_results = Restaurant.objects.all()
            menu_results = Menu.objects.none()
        
        # Apply category filter
        if category:
            resto_results = resto_results.filter(description__icontains=category)
        
        # Apply rating filter
        if min_rating:
            resto_results = resto_results.annotate(
                avg_rating=Avg('review__rating')
            ).filter(avg_rating__gte=float(min_rating))
            
    else:
        resto_results = Restaurant.objects.none()
        menu_results = Menu.objects.none()

    restaurants_all = Restaurant.objects.all()

    top_rated = Restaurant.objects.annotate(
        avg_rating=Avg('review__rating')
    ).filter(avg_rating__isnull=False).order_by('-avg_rating')[:5]

    # Get random reviews from different restaurants
    last_reviews = Review.objects.select_related('user', 'restaurant').order_by('?')[:5]

    # ✅ Siapkan data sebagai list biasa (jangan json.dumps!)
    restaurants_data = []
    for resto in restaurants_all:
        try:
            restaurants_data.append({
                'name': str(resto.name).strip(),
                'lat': float(resto.latitude),
                'lng': float(resto.longitude),
                'url': f"/restaurants/detail/{resto.id}/",
            })
        except (ValueError, TypeError, AttributeError):
            continue

    # ✅ Jangan json.dumps() → biarkan |json_script yang handle
    restaurants_json = restaurants_data
    
    # Get recently viewed restaurants for logged in users
    recently_viewed = get_recently_viewed_restaurants(request.user) if request.user.is_authenticated else []

    context = {
        'query': query,
        'category': category,
        'min_rating': min_rating,
        'resto_results': resto_results,
        'menu_results': menu_results,
        'top_rated': top_rated,
        'last_reviews': last_reviews,
        'restaurants_all': restaurants_all,
        'restaurants_json': restaurants_json,
        'bookmarked_resto_ids': [],
        'categories': ['China', 'Jepang', 'Western', 'Indonesia', 'Fast Food', 'Italian'],
        'recently_viewed': recently_viewed,
    }
    return render(request, 'core/home.html', context)

def explore(request):
    tab = request.GET.get('tab', 'recommendation')
    context = {'tab': tab}

    if request.user.is_authenticated:
        context['bookmarked_resto_ids'] = list(
            Bookmark.objects.filter(user=request.user).values_list('restaurant_id', flat=True)
        )

    if tab == 'recommendation' and request.user.is_authenticated:
        # 🔥 Gunakan sistem rekomendasi AI sederhana
        context['restaurants'] = simple_recommendation(request.user)

    elif tab == 'top_rated':
        context['restaurants'] = Restaurant.objects.annotate(
            avg_rating=Avg('review__rating')
        ).filter(avg_rating__isnull=False).order_by('-avg_rating')[:20]

    elif tab == 'near_you':
        context['restaurants'] = Restaurant.objects.annotate(
            avg_rating=Avg('review__rating')
        ).order_by('?')[:20]

    elif tab == 'all':
        qs = Restaurant.objects.annotate(
            avg_rating=Avg('review__rating'),
            review_count=Count('review')
        ).order_by('name')

        paginator = Paginator(qs, 12)  # 12 per page
        page = request.GET.get('page', 1)

        try:
            restaurants_page = paginator.page(page)
        except PageNotAnInteger:
            restaurants_page = paginator.page(1)
        except EmptyPage:
            restaurants_page = paginator.page(paginator.num_pages)

        context['restaurants'] = restaurants_page

    elif tab == 'saved' and request.user.is_authenticated:
        bookmarks = Bookmark.objects.filter(user=request.user).select_related('restaurant')
        context['restaurants'] = [b.restaurant for b in bookmarks]
        for resto in context['restaurants']:
            reviews = resto.review_set.all()
            resto.avg_rating = round(sum([r.rating for r in reviews]) / len(reviews), 1) if reviews else 0
            resto.review_count = len(reviews)

    return render(request, 'core/explore.html', context)