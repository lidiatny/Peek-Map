# core/recommendations.py
from collections import defaultdict
from django.db.models import Avg, Q, Count
from restaurants.models import Restaurant
from reviews.models import Review
from accounts.models import Bookmark


def get_user_activity_preferences(user):
    """
    Get user preferences from activity tracking
    """
    if not user.is_authenticated:
        return {}
    
    try:
        from .models import UserActivity
        
        # Get frequently viewed restaurants
        viewed_restaurants = UserActivity.objects.filter(
            user=user,
            activity_type='view',
            restaurant__isnull=False
        ).values_list('restaurant_id', flat=True)
        
        viewed_count = defaultdict(int)
        for resto_id in viewed_restaurants:
            viewed_count[resto_id] += 1
            
        # Get search patterns
        search_queries = UserActivity.objects.filter(
            user=user,
            activity_type='search',
            search_query__isnull=False
        ).values_list('search_query', flat=True)
        
        search_keywords = defaultdict(int)
        for query in search_queries:
            words = query.lower().split()
            for word in words:
                search_keywords[word] += 1
        
        return {
            'viewed_restaurants': dict(viewed_count),
            'search_keywords': dict(search_keywords)
        }
    except ImportError:
        return {}

def get_user_preferences(user):
    """
    Ambil preferensi user dari:
    - Rating tinggi
    - Komentar (ekstrak kata kunci)
    - Bookmark
    """
    reviews = Review.objects.filter(user=user)
    bookmarks = Bookmark.objects.filter(user=user)

    # Kata kunci dari komentar
    keywords = defaultdict(int)
    high_rated_resto_ids = set()

    for review in reviews:
        if review.rating >= 4:
            high_rated_resto_ids.add(review.restaurant.id)
        # Ekstrak kata kunci sederhana
        comment = review.comment.lower()
        words = comment.split()
        for word in ['enak', 'lezat', 'pedas', 'murah', 'mahal', 'nyaman', 'ramai', 'cepat', 'lambat', 'ramai']:
            if word in words:
                keywords[word] += 1

    bookmarked_resto_ids = set(bookmarks.values_list('restaurant_id', flat=True))

    return {
        'high_rated': high_rated_resto_ids,
        'keywords': dict(keywords),
        'bookmarked': bookmarked_resto_ids
    }

def simple_recommendation(user):
    """
    Rekomendasi berdasarkan:
    1. Restoran dengan rating tinggi global
    2. Mirip dengan restoran yang pernah di-rate tinggi
    3. Kata kunci dari komentar
    4. Belum pernah di-review atau di-bookmark
    """
    if not user.is_authenticated:
        return Restaurant.objects.annotate(
            avg_rating=Avg('review__rating')
        ).filter(avg_rating__isnull=False).order_by('-avg_rating')[:10]

    # Ambil preferensi user dari review dan bookmark
    prefs = get_user_preferences(user)
    
    # Ambil preferensi dari activity tracking
    activity_prefs = get_user_activity_preferences(user)

    all_resto = Restaurant.objects.annotate(
        avg_rating=Avg('review__rating'),
        review_count=Count('review')
    ).filter(avg_rating__isnull=False)

    # Hilangkan yang sudah di-review atau di-bookmark
    reviewed_ids = Review.objects.filter(user=user).values_list('restaurant_id', flat=True)
    exclude_ids = set(reviewed_ids) | prefs['bookmarked']
    candidates = all_resto.exclude(id__in=exclude_ids)

    # Skor rekomendasi
    scored = []
    for resto in candidates:
        score = 0.0

        # 1. Jika restoran mirip dengan yang pernah di-rate tinggi (sederhana: nama mengandung kata umum)
        for hr_id in prefs['high_rated']:
            hr = Restaurant.objects.get(id=hr_id)
            if hr.name.lower() in resto.name.lower() or resto.name.lower() in hr.name.lower():
                score += 2.0

        # 2. Kata kunci dari komentar
        name_lower = resto.name.lower()
        address_lower = resto.address.lower()
        text = name_lower + " " + address_lower
        for keyword, weight in prefs['keywords'].items():
            if keyword in text:
                score += weight * 1.5

        # 3. Rating rata-rata tinggi
        if resto.avg_rating >= 4.0:
            score += 2.0
        elif resto.avg_rating >= 3.5:
            score += 1.0

        # 4. Banyak review (populer)
        if resto.review_count >= 10:
            score += 1.0
            
        # 5. Boost berdasarkan activity tracking
        if activity_prefs:
            # Boost jika user sering view restaurant serupa
            for viewed_id, view_count in activity_prefs.get('viewed_restaurants', {}).items():
                if viewed_id != resto.id:
                    viewed_resto = Restaurant.objects.filter(id=viewed_id).first()
                    if viewed_resto and viewed_resto.name.lower() in resto.name.lower():
                        score += view_count * 0.5
                        
            # Boost berdasarkan search keywords
            resto_text = f"{resto.name} {resto.description}".lower()
            for keyword, count in activity_prefs.get('search_keywords', {}).items():
                if keyword in resto_text:
                    score += count * 0.3

        if score > 0:
            scored.append((resto, score))

    # Urutkan berdasarkan skor
    scored.sort(key=lambda x: x[1], reverse=True)
    return [item[0] for item in scored[:10]]