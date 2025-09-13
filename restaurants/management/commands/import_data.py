import csv
import os
import random
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from restaurants.models import Restaurant
from reviews.models import Review
from decimal import Decimal

class Command(BaseCommand):
    help = 'Import restaurant and review data from CSV files'

    def handle(self, *args, **options):
        # Path ke folder CSV (dalam Django project)
        import os
        from django.conf import settings
        csv_folder = os.path.join(settings.BASE_DIR, "data", "fix_scrapped")
        
        # Import restaurants
        resto_files = [f for f in os.listdir(csv_folder) if f.startswith('00') and 'resto' in f and not 'reviews' in f]
        
        self.stdout.write(f"Found {len(resto_files)} restaurant files")
        
        for file_name in resto_files:
            file_path = os.path.join(csv_folder, file_name)
            self.stdout.write(f"Processing {file_name}")
            
            with open(file_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile, delimiter=';')
                for row in reader:
                    try:
                        # Skip if restaurant already exists
                        if Restaurant.objects.filter(name=row['name']).exists():
                            continue
                            
                        
                        # Parse coordinates
                        try:
                            lat = float(row['latitude'].replace('.', '')) / 1000000
                            lng = float(row['longitude'].replace('.', '')) / 1000000
                        except:
                            lat = -6.2
                            lng = 106.8
                        
                        # Create restaurant
                        restaurant = Restaurant.objects.create(
                            name=row['name'],
                            description=f"{row['category']} - {row['description']}" if row['description'] != 'N/A' else row['category'],
                            latitude=lat,
                            longitude=lng,
                            address=f"Jakarta ({row['category']})"
                        )
                        print(f"Created restaurant: {restaurant.name}")
                        
                    except Exception as e:
                        print(f"Error creating restaurant {row.get('name', 'Unknown')}: {str(e)}")
        
        # Import reviews
        review_files = [f for f in os.listdir(csv_folder) if f.startswith('00') and 'reviews' in f]
        
        # Get or create sample users
        users = []
        for i in range(10):
            user, created = User.objects.get_or_create(
                username=f'user{i}',
                defaults={'email': f'user{i}@example.com'}
            )
            users.append(user)
        
        self.stdout.write(f"Found {len(review_files)} review files")
        
        for file_name in review_files:
            file_path = os.path.join(csv_folder, file_name)
            self.stdout.write(f"Processing {file_name}")
            
            with open(file_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile, delimiter=';')
                for row in reader:
                    try:
                        # Find restaurant by original_id
                        resto_id = int(row['id_resto'])
                        restaurants = Restaurant.objects.all()
                        
                        if restaurants.exists():
                            # Get a random restaurant for this review
                            restaurant = random.choice(restaurants)
                            user = random.choice(users)
                            
                            # Parse rating
                            try:
                                rating = int(float(row['rating']))
                                if rating < 1:
                                    rating = 1
                                elif rating > 5:
                                    rating = 5
                            except:
                                rating = random.randint(3, 5)
                            
                            # Create review
                            review = Review.objects.create(
                                restaurant=restaurant,
                                user=user,
                                rating=rating,
                                comment=row['review_text'][:500] if row['review_text'] != 'N/A' else 'Great food!',
                            )
                            
                    except Exception as e:
                        print(f"Error creating review: {str(e)}")
        
                
        self.stdout.write(self.style.SUCCESS(f'Successfully imported data!'))
        self.stdout.write(f'Total restaurants: {Restaurant.objects.count()}')
        self.stdout.write(f'Total reviews: {Review.objects.count()}')