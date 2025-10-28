# core/views.py
from django.shortcuts import render, redirect
from django.db.models import Avg, Value, Count, Case, When, IntegerField
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models.functions import Coalesce
from restaurants.models import Restaurant, Menu
from reviews.models import Review
from .utils import track_user_activity, get_recently_viewed_restaurants
from django.db.models import Q
from accounts.models import Bookmark
from .recommendations import simple_recommendation


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

def _ids_from_recommendation(rec):
    """
    Terima apa saja dari simple_recommendation:
    - QuerySet Restaurant
    - list Restaurant
    - list id (int/str)
    Balikin list[int] berisi ID valid.
    """
    if hasattr(rec, "values_list"):
        return list(rec.values_list("id", flat=True))
    ids = []
    for item in (rec or []):
        if hasattr(item, "id"):           # Restaurant instance
            ids.append(item.id)
        else:
            try:
                ids.append(int(item))     # already id-like
            except (TypeError, ValueError):
                continue
    return ids

@login_required(login_url="/accounts/login/")
def explore(request):
    tab = (request.GET.get("tab") or "all").strip()
    user = request.user

    # base queryset
    qs = Restaurant.objects.all()

    if tab == "recommendation":
        rec_raw = simple_recommendation(user) or []
        rec_ids = _ids_from_recommendation(rec_raw)

        if rec_ids:
            ordering = Case(
                *[When(id=pk, then=pos) for pos, pk in enumerate(rec_ids)],
                output_field=IntegerField()
            )
            qs = Restaurant.objects.filter(id__in=rec_ids).order_by(ordering)
        else:
            qs = Restaurant.objects.none()

    elif tab == "top_rated":
        qs = qs.annotate(avg=Coalesce(Avg("reviews__rating"), 0.0)).order_by("-avg")

    elif tab == "near_you":
        qs = qs.order_by("?")

    elif tab == "saved":
        saved_ids = Bookmark.objects.filter(user=user).values_list("restaurant_id", flat=True)
        qs = qs.filter(id__in=saved_ids)

    else:  # "all"
        qs = qs.order_by("name")

    # pastikan semua queryset punya field yang dipakai di template card
    qs = qs.annotate(
        rating_avg=Coalesce(Avg("reviews__rating"), 0.0),
        reviews_cnt=Count("reviews", distinct=True),
    )

    # pagination
    paginator = Paginator(qs, 9)  # 9 cards per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # saved state utk tombol "Save"
    bookmarked_resto_ids = set(
        Bookmark.objects.filter(user=user).values_list("restaurant_id", flat=True)
    )

    return render(request, "core/explore.html", {
        "tab": tab,
        "restaurants": page_obj,
        "page_obj": page_obj,
        "bookmarked_resto_ids": bookmarked_resto_ids,
    })