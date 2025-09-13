from .models import UserActivity


def track_user_activity(user, activity_type, restaurant=None, search_query=None):
    """
    Simple utility function to track user activities
    """
    if user.is_authenticated:
        try:
            UserActivity.objects.create(
                user=user,
                restaurant=restaurant,
                activity_type=activity_type,
                search_query=search_query
            )
        except Exception:
            # Fail silently to not break the main functionality
            pass


def get_recently_viewed_restaurants(user, limit=5):
    """
    Get recently viewed restaurants by user
    """
    if not user.is_authenticated:
        return []
    
    recent_activities = UserActivity.objects.filter(
        user=user,
        activity_type='view',
        restaurant__isnull=False
    ).select_related('restaurant').order_by('-timestamp')
    
    # Manual distinct untuk SQLite compatibility
    seen_restaurants = set()
    unique_restaurants = []
    
    for activity in recent_activities:
        if activity.restaurant.id not in seen_restaurants:
            seen_restaurants.add(activity.restaurant.id)
            unique_restaurants.append(activity.restaurant)
            if len(unique_restaurants) >= limit:
                break
    
    return unique_restaurants


def get_user_search_history(user, limit=10):
    """
    Get user's search history
    """
    if not user.is_authenticated:
        return []
    
    search_activities = UserActivity.objects.filter(
        user=user,
        activity_type='search',
        search_query__isnull=False
    ).values_list('search_query', flat=True)[:limit]
    
    return list(search_activities)