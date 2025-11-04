from django.shortcuts import render
from django.db.models import Q, Avg, Value, FloatField, Count, Case, When, IntegerField
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models.functions import Coalesce

from restaurants.models import Restaurant, Menu
from reviews.models import Review
from accounts.models import Bookmark

from .utils import track_user_activity, get_recently_viewed_restaurants
from .recommendations import simple_recommendation  # masih dipakai di explore (tab recommendation)w


def home(request):
    query = (request.GET.get('q') or '').strip()
    category = (request.GET.get('category') or '').strip()
    min_rating = (request.GET.get('min_rating') or '').strip()

    # Normalisasi pilihan kategori dari UI -> value di DB
    CATEGORY_MAP = {
        'China': 'Chinese',
        'Chinese': 'Chinese',
        'Jepang': 'Japanese',
        'Japanese': 'Japanese',
        'Western': 'Western',
        'Indonesia': 'Indonesian',
        'Indonesian': 'Indonesian',
        'All': '',
        'All Categories': '',
        'Semua': '',
    }
    canon_cat = CATEGORY_MAP.get(category, category).strip()

    # base queryset
    resto_results = Restaurant.objects.all()
    menu_results = Menu.objects.none()

    # === CATEGORY FILTER ===
    if canon_cat and canon_cat.lower() not in ('all', 'all categories', 'semua'):
        resto_results = resto_results.filter(cuisine_type__iexact=canon_cat)

    # === HYBRID SEARCH (TF-IDF + SBERT + location boost) ===
    rank_ids = []
    if query:
        if request.user.is_authenticated:
            track_user_activity(request.user, 'search', search_query=query)

        # ambil ranking dari engine (cukup banyak sebelum difilter)
        try:
            rank_ids = recommend_by_query(query, top_n=120, location_boost=1.4)
        except Exception:
            rank_ids = []

        if rank_ids:
            # batasi awal dengan hasil engine
            resto_results = resto_results.filter(id__in=rank_ids)
        else:
            # fallback LIKE kalau engine/artefak belum siap
            resto_results = (resto_results.filter(
                Q(name__icontains=query) |
                Q(menus__name__icontains=query)
            ).distinct())

        # (opsional) tetap kirim match menu untuk UI kecil
        menu_results = Menu.objects.filter(name__icontains=query).select_related('restaurant')

    # === MIN RATING FILTER ===
    if min_rating:
        clean = ''.join(ch for ch in str(min_rating) if ch.isdigit() or ch == '.')
        try:
            thr = float(clean)
        except ValueError:
            thr = 0.0

        resto_results = (
            resto_results
            .annotate(rating_avg=Coalesce(Avg('reviews__rating'), Value(0.0), output_field=FloatField()))
            .filter(rating_avg__gte=thr)
        )

    # === ORDER BY RELEVANCE (kalau ada rank_ids dari engine) ===
    if rank_ids:
        # urutkan sesuai ranking engine
        ordering = Case(*[When(id=pk, then=pos) for pos, pk in enumerate(rank_ids)],
                        output_field=IntegerField())
        resto_results = resto_results.order_by(ordering)
    else:
        # jika tidak pakai engine, boleh default by name supaya stabil
        if query or category or min_rating:
            resto_results = resto_results.order_by('name')

    # jika tidak ada filter apapun, kosongkan hasil (agar section Search Results tidak muncul)
    if not query and not category and not min_rating:
        resto_results = Restaurant.objects.none()
        menu_results = Menu.objects.none()

    # === Pagination (9 per halaman) ===
    page = request.GET.get('page', 1)
    paginator = Paginator(resto_results, 9)
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    # === Data lain untuk home ===
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
                'lat': float(getattr(resto, 'latitude', None)),
                'lng': float(getattr(resto, 'longitude', None)),
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

        'page_obj': page_obj,
        'paginator': paginator,
        'results_count': paginator.count,

        'menu_results': menu_results,
        'top_rated': top_rated,
        'last_reviews': last_reviews,
        'restaurants_all': restaurants_all,
        'restaurants_json': restaurants_json,
        'bookmarked_resto_ids': [],
        'categories': ['Chinese', 'Japanese', 'Western', 'Indonesian'],
        'recently_viewed': recently_viewed,
    }
    return render(request, 'core/home.html', context)


# ----------------- RECOMMENDATION SECTION (Explore) --------------------

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

    paginator = Paginator(qs, 12)
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
