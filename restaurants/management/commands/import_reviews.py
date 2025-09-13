import csv
import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from restaurants.models import Restaurant
from reviews.models import Review

class Command(BaseCommand):
    help = 'Import reviews from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument("file_path", type=str, help="Path to the reviews CSV file")

    def handle(self, *args, **options):
        from django.conf import settings
        reviews_file = os.path.join(settings.BASE_DIR, "data", "reviews.csv")
        
        if not os.path.exists(reviews_file):
            print(f"File {reviews_file} not found!")
            return
        
        # Create sample users (user1 - user20)
        users = []
        for i in range(1, 21):
            user, created = User.objects.get_or_create(
                username=f'user{i}',
                defaults={
                    'email': f'user{i}@example.com',
                    'first_name': 'User',
                    'last_name': str(i)
                }
            )
            users.append(user)
            if created:
                print(f"Created user: user{i}")
        
        restaurants = list(Restaurant.objects.all())
        if not restaurants:
            print("No restaurants found! Please import restaurants first.")
            return
        
        imported_count = 0
        
        with open(reviews_file, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                try:
                    # Get user
                    user_id = int(row['user_id']) - 1
                    if user_id >= len(users):
                        user_id = user_id % len(users)
                    user = users[user_id]
                    
                    # Get restaurant
                    restaurant_id = int(row['restaurant_id']) - 1
                    if restaurant_id >= len(restaurants):
                        restaurant_id = restaurant_id % len(restaurants)
                    restaurant = restaurants[restaurant_id]
                    
                    # Parse rating
                    rating = int(float(row['rating']))
                    rating = max(1, min(5, rating))
                    
                    # Check unique constraint (only one review per user per restaurant)
                    if Review.objects.filter(user=user, restaurant=restaurant).exists():
                        continue
                    
                    # Create review
                    Review.objects.create(
                        restaurant=restaurant,
                        user=user,
                        rating=rating,
                        comment=row['review_text'] or '',
                    )
                    
                    imported_count += 1
                    if imported_count % 100 == 0:
                        print(f"Imported {imported_count} reviews...")
                        
                except Exception as e:
                    print(f"Error importing review: {str(e)}")
                    continue
        
        print(f"✅ Successfully imported {imported_count} reviews!")
        print(f"📌 Total restaurants: {Restaurant.objects.count()}")
        print(f"📌 Total reviews: {Review.objects.count()}")
        print(f"📌 Total users: {User.objects.count()}")
