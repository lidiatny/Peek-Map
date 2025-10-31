from django.shortcuts import render, redirect
from django.db.models import Q, Avg, F, Value, FloatField, Count, Case, When, IntegerField
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models.functions import Coalesce
from restaurants.models import Restaurant, Menu
from reviews.models import Review
from .utils import track_user_activity, get_recently_viewed_restaurants
from accounts.models import Bookmark
from .recommendations import simple_recommendation


def home(request):
    query = (request.GET.get('q') or '').strip()
    category = (request.GET.get('category') or '').strip()
    min_rating = (request.GET.get('min_rating') or '').strip()

    # normalize UI category → database field value
    CATEGORY_MAP = {
        'China': 'Chinese',
        'Chinese': 'Chinese',
        'Jepang': 'Japanese',
        'Japanese': 'Japanese',
        'Western': 'Western',
        'Indonesia': 'Indonesian',
        'Indonesian': 'Indonesian',
    }

    canon_cat = CATEGORY_MAP.get(category, category).strip()

    # start with all restaurants
    resto_results = Restaurant.objects.all()
    menu_results = Menu.objects.none()

    # === CATEGORY FILTER ALWAYS RUNS ===
    if canon_cat and canon_cat.lower() not in ('all', 'all categories', 'semua'):
        resto_results = resto_results.filter(cuisine_type__iexact=canon_cat)

    # === SEARCH / KEYWORD ===
    if query:
        if request.user.is_authenticated:
            track_user_activity(request.user, 'search', search_query=query)

        resto_results = resto_results.filter(
            Q(name__icontains=query) |
            Q(menus__name__icontains=query)
        ).distinct()

        menu_results = Menu.objects.filter(name__icontains=query).select_related('restaurant')

    # === MIN RATING ===
    if min_rating:
        clean = ''.join(ch for ch in str(min_rating) if ch.isdigit() or ch == '.')
        try:
            thr = float(clean)
        except ValueError:
            thr = 0.0

        resto_results = (
            resto_results
            .annotate(
                rating_avg=Coalesce(Avg('reviews__rating'), Value(0.0), output_field=FloatField()),
            )
            .filter(rating_avg__gte=thr)
        )

    # if user not searching anything → no results
    if not query and not category and not min_rating:
        resto_results = Restaurant.objects.none()
        menu_results = Menu.objects.none()

    # === Data for other sections ===
    restaurants_all = Restaurant.objects.all()

    top_rated = (
        Restaurant.objects
        .annotate(rating_avg=Coalesce(Avg('reviews__rating'), 0.0))
        .filter(rating_avg__gt=0)
        .order_by('-rating_avg')[:5]
    )

    last_reviews = Review.objects.select_related('user', 'restaurant').order_by('?')[:5]

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
        'categories': ['Chinese', 'Japanese', 'Western', 'Indonesian'],  # dropdown values
        'recently_viewed': recently_viewed,
    }

    return render(request, 'core/home.html', context)


# ----------------- RECOMMENDATION SECTION --------------------

def _ids_from_recommendation(rec):
    if hasattr(rec, "values_list"):
        return list(rec.values_list("id", flat=True))
    ids = []
    for item in (rec or []):
        if hasattr(item, "id"):
            ids.append(item.id)
        else:
            try:
                ids.append(int(item))
            except (TypeError, ValueError):
                continue
    return ids


@login_required(login_url="/accounts/login/")
def explore(request):
    tab = (request.GET.get("tab") or "all").strip()
    user = request.user

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

    else:
        qs = qs.order_by("name")

    qs = qs.annotate(
        rating_avg=Coalesce(Avg("reviews__rating"), 0.0),
        reviews_cnt=Count("reviews", distinct=True),
    )

    paginator = Paginator(qs, 9)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    bookmarked_resto_ids = set(
        Bookmark.objects.filter(user=user).values_list("restaurant_id", flat=True)
    )

    return render(request, "core/explore.html", {
        "tab": tab,
        "restaurants": page_obj,
        "page_obj": page_obj,
        "bookmarked_resto_ids": bookmarked_resto_ids,
    })
