# core/views.py
from django.shortcuts import render
from django.db.models import Avg, Count
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage

from django.db.models.functions import Coalesce

from restaurants.models import Restaurant, Menu
from reviews.models import Review
from accounts.models import Bookmark

from .recommendations import simple_recommendation
from .utils import track_user_activity, get_recently_viewed_restaurants
from django.db.models import Q


def home(request):
    query = (request.GET.get('q') or '').strip()
    category = (request.GET.get('category') or '').strip()
    min_rating = (request.GET.get('min_rating') or '').strip()

    CATEGORY_MAP = {
        'China': 'Chinese',
        'Jepang': 'Japanese',
        'Western': 'Western',
        'Indonesia': 'Indonesian',
        'Italian': 'Italian',
    }

    canon_cat = CATEGORY_MAP.get(category, category)  # fallback: pakai mentah

    resto_results = Restaurant.objects.none()
    menu_results = Menu.objects.none()

    # === Search & filters ===
    if query or category or min_rating:

        if query:
            if request.user.is_authenticated:
                track_user_activity(request.user, 'search', search_query=query)
            resto_results = (
                Restaurant.objects
                .filter(
                    Q(name__icontains=query) |
                    Q(menus__name__icontains=query)   # reverse FK Menu -> Restaurant
                )
                .distinct()
            )
            menu_results = Menu.objects.filter(name__icontains=query).select_related('restaurant')
        else:
            resto_results = Restaurant.objects.all()

        if canon_cat:
            resto_results = resto_results.filter(
                Q(type__iexact=canon_cat) |              # ← pakai field yang benar
                Q(description__icontains=canon_cat) 
            )

        if min_rating:
            try:
                thr = float(min_rating)
            except ValueError:
                thr = 0.0
            resto_results = (
                resto_results
                .annotate(rating_avg=Coalesce(Avg('reviews__rating'), 0.0))
                .filter(rating_avg__gte=thr)
            )
    else:
        resto_results = Restaurant.objects.none()
        menu_results = Menu.objects.none()

    restaurants_all = Restaurant.objects.all()

    top_rated = (
        Restaurant.objects
        .annotate(rating_avg=Coalesce(Avg('reviews__rating'), 0.0))
        .filter(rating_avg__gt=0)
        .order_by('-rating_avg')[:5]
    )

    # random recent reviews
    last_reviews = Review.objects.select_related('user', 'restaurant').order_by('?')[:5]

    # map data
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
    restaurants_json = restaurants_data

    recently_viewed = get_recently_viewed_restaurants(request.user) if request.user.is_authenticated else []

    context = {
        'query': query,
        'category': category,
        'min_rating': min_rating,
        'resto_results': resto_results,
        'menu_results': menu_results,
        'results_count': resto_results.count(),
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
        # simple_recommendation mungkin balikin list/qs tanpa annotate.
        base = simple_recommendation(request.user)
        ids = [r.id for r in base]             # aman untuk list/qs
        context['restaurants'] = (
            Restaurant.objects.filter(id__in=ids)
            .annotate(
                rating_avg=Coalesce(Avg('reviews__rating'), 0.0),
                reviews_cnt=Count('reviews', distinct=True)
            )
        )

    elif tab == 'top_rated':
        context['restaurants'] = (
            Restaurant.objects
            .annotate(
                rating_avg=Coalesce(Avg('reviews__rating'), 0.0),
                reviews_cnt=Count('reviews', distinct=True)
            )
            .filter(rating_avg__gt=0)
            .order_by('-rating_avg')[:20]
        )

    elif tab == 'near_you':
        context['restaurants'] = (
            Restaurant.objects
            .annotate(
                rating_avg=Coalesce(Avg('reviews__rating'), 0.0),
                reviews_cnt=Count('reviews', distinct=True)
            )
            .order_by('?')[:20]
        )

    elif tab == 'all':
        qs = (
            Restaurant.objects
            .annotate(
                rating_avg=Coalesce(Avg('reviews__rating'), 0.0),
                # jangan pakai nama field asli kalau kamu memang punya field review_count di model
                reviews_cnt=Count('reviews', distinct=True)
            )
            .order_by('name')
        )
        paginator = Paginator(qs, 12)
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
        restos = [b.restaurant for b in bookmarks]
        for r in restos:
            reviews = r.reviews.all()   # kalau kamu pakai related_name='reviews', ganti ke r.reviews.all()
            r.reviews_cnt = reviews.count()
            r.rating_avg = round(sum((rv.rating or 0) for rv in reviews) / len(reviews), 1) if reviews else 0.0
        context['restaurants'] = restos

    return render(request, 'core/explore.html', context)
