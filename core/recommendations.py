# core/recommendations.py
# -------------------------------------------------
# Rekomendasi restoran berbasis aktivitas, review, dan popularitas.
# Konsisten menggunakan annotation:
#   - rating_avg : float (rata-rata rating, Coalesce ke 0.0)
#   - rating_cnt : int   (jumlah review, distinct)
# Hindari tabrakan nama dengan field 'rating' di Restaurant.
# -------------------------------------------------

from collections import defaultdict
from typing import Dict, Iterable, List, Tuple

from django.db.models import Avg, Count, Q, QuerySet
from django.db.models.functions import Coalesce

from restaurants.models import Restaurant
from reviews.models import Review
from accounts.models import Bookmark


# UBAH ke "reviews" jika di model Review kamu pakai related_name='reviews'
REVIEW_REL = "review"   # default reverse lookup untuk FK tanpa related_name


def _base_queryset() -> QuerySet:
    """
    QuerySet dasar dengan annotation aman:
      - rating_avg: rata-rata rating (0.0 jika belum ada review)
      - rating_cnt: jumlah review (distinct)
    """
    return (
        Restaurant.objects
        .annotate(
            rating_avg=Coalesce(Avg(f"{REVIEW_REL}__rating"), 0.0),
            rating_cnt=Count(REVIEW_REL, distinct=True),
        )
    )


def get_user_activity_preferences(user) -> Dict:
    """
    Preferensi dari activity tracking (view & search).
    Aman kalau tabel UserActivity belum ada (ImportError).
    """
    if not user.is_authenticated:
        return {}

    try:
        from .models import UserActivity

        viewed_restaurants = UserActivity.objects.filter(
            user=user,
            activity_type="view",
            restaurant__isnull=False,
        ).values_list("restaurant_id", flat=True)

        viewed_count = defaultdict(int)
        for rid in viewed_restaurants:
            viewed_count[rid] += 1

        search_queries = UserActivity.objects.filter(
            user=user,
            activity_type="search",
            search_query__isnull=False,
        ).values_list("search_query", flat=True)

        search_keywords = defaultdict(int)
        for query in search_queries:
            if not query:
                continue
            for word in query.lower().split():
                search_keywords[word] += 1

        return {
            "viewed_restaurants": dict(viewed_count),
            "search_keywords": dict(search_keywords),
        }
    except ImportError:
        return {}


def get_user_preferences(user) -> Dict:
    """
    Preferensi user dari Review & Bookmark.
      - high_rated: id restoran yang pernah di-rate >= 4
      - keywords : kata kunci sederhana dari komentar
      - bookmarked: id restoran yang di-bookmark
    """
    reviews = Review.objects.filter(user=user)
    bookmarks = Bookmark.objects.filter(user=user)

    keywords = defaultdict(int)
    high_rated_resto_ids = set()

    for rv in reviews:
        if rv.rating is not None and rv.rating >= 4:
            if rv.restaurant_id:
                high_rated_resto_ids.add(rv.restaurant_id)

        comment = (rv.comment or "").lower()
        words = comment.split()
        for word in [
            "enak",
            "lezat",
            "pedas",
            "murah",
            "mahal",
            "nyaman",
            "ramai",
            "cepat",
            "lambat",
        ]:
            if word in words:
                keywords[word] += 1

    bookmarked_resto_ids = set(bookmarks.values_list("restaurant_id", flat=True))

    return {
        "high_rated": high_rated_resto_ids,
        "keywords": dict(keywords),
        "bookmarked": bookmarked_resto_ids,
    }


def _score_candidates(
    user_prefs: Dict,
    activity_prefs: Dict,
    candidates: Iterable[Restaurant],
) -> List[Tuple[Restaurant, float]]:
    """
    Hitung skor untuk masing-masing kandidat restoran.
    Menggunakan:
      - kemiripan nama dengan high_rated
      - kemunculan keywords
      - rating_avg & review_count (popularity)
      - booster dari activity (view/search)
    """
    scored: List[Tuple[Restaurant, float]] = []

    # Preload nama restoran untuk high_rated & viewed agar hemat query
    high_rated_ids = list(user_prefs.get("high_rated", []))
    id_to_name_hr = {
        r["id"]: r["name"].lower()
        for r in Restaurant.objects.filter(id__in=high_rated_ids).values("id", "name")
    }

    viewed_map: Dict[int, int] = activity_prefs.get("viewed_restaurants", {}) or {}
    id_to_name_viewed = {
        r["id"]: r["name"].lower()
        for r in Restaurant.objects.filter(id__in=list(viewed_map.keys())).values("id", "name")
    }

    keyword_weights: Dict[str, int] = user_prefs.get("keywords", {}) or {}

    for resto in candidates:
        score = 0.0

        name_lower = (resto.name or "").lower()
        addr_lower = (resto.address or "").lower()
        desc_lower = (resto.description or "").lower()
        text_all = f"{name_lower} {addr_lower} {desc_lower}"

        # 1) Kemiripan sangat sederhana via substring dengan high_rated names
        for hr_id, hr_name in id_to_name_hr.items():
            if hr_id == resto.id:
                continue
            if hr_name and (hr_name in name_lower or name_lower in hr_name):
                score += 2.0

        # 2) Keyword dari komentar
        for kw, wt in keyword_weights.items():
            if kw and kw in text_all:
                score += float(wt) * 1.5

        # 3) Rating rata-rata tinggi (pakai annotation 'rating_avg')
        if getattr(resto, "rating_avg", 0.0) >= 4.0:
            score += 2.0
        elif getattr(resto, "rating_avg", 0.0) >= 3.5:
            score += 1.0

        # 4) Popularitas dari field review_count (field di model kamu)
        if (resto.review_count or 0) >= 10:
            score += 1.0

        # 5) Booster dari activity (viewed & search keywords)
        if activity_prefs:
            # a) kemiripan nama dengan yang sering dilihat
            for viewed_id, vcount in viewed_map.items():
                if viewed_id == resto.id:
                    continue
                vname = id_to_name_viewed.get(viewed_id, "")
                if vname and (vname in name_lower or name_lower in vname):
                    score += float(vcount) * 0.5

            # b) search keywords
            for kw, cnt in (activity_prefs.get("search_keywords") or {}).items():
                if kw and kw in text_all:
                    score += float(cnt) * 0.3

        if score > 0:
            scored.append((resto, score))

    return scored


def simple_recommendation(user) -> List[Restaurant]:
    """
    Rekomendasi final:
      - Guest  : top by rating_avg (global).
      - Logged : kandidat = restoran yang belum di-review/bookmark,
                 lalu diberi skor dan diurutkan.
    Return: list of Restaurant (maks 10 item).
    """
    # Guest → gunakan satu jalur yang sama dan konsisten
    if not user.is_authenticated:
        qs = _base_queryset().order_by("-rating_avg", "-rating_cnt", "name")
        return list(qs[:10])

    # Preferensi user (review, bookmark) + activity
    prefs = get_user_preferences(user)
    activity_prefs = get_user_activity_preferences(user)

    # Semua restoran dengan annotation dasar
    all_resto = _base_queryset().order_by("-rating_avg", "-rating_cnt", "name")

    # Hilangkan yang sudah direview atau di-bookmark
    reviewed_ids = set(
        Review.objects.filter(user=user).values_list("restaurant_id", flat=True)
    )
    exclude_ids = reviewed_ids | prefs.get("bookmarked", set())
    candidates = all_resto.exclude(id__in=list(exclude_ids))

    # Skoring
    scored = _score_candidates(prefs, activity_prefs, candidates)

    # Urutkan & ambil top-N
    scored.sort(key=lambda x: x[1], reverse=True)
    top = [item[0] for item in scored[:10]]

    # Fallback: kalau skor kosong, pakai top global
    if not top:
        return list(all_resto[:10])

    return top
