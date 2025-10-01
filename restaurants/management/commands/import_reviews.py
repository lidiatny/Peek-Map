import csv, os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from restaurants.models import Restaurant
from reviews.models import Review
from django.conf import settings

def open_csv(path):
    import csv
    f = open(path, 'r', encoding='utf-8-sig', newline='')
    sample = f.read(4096)
    f.seek(0)
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=',;')
    except Exception:
        dialect = csv.excel
    return f, dialect

class Command(BaseCommand):
    help = 'Import reviews from data/reviews.csv (support restaurant_id or restaurant_name).'

    def add_arguments(self, parser):
        parser.add_argument("--file", type=str, default=None,
                            help="Path to reviews CSV. Default: data/reviews.csv")

    def handle(self, *args, **options):
        reviews_path = options["file"] or os.path.join(settings.BASE_DIR, "data", "reviews.csv")
        if not os.path.exists(reviews_path):
            self.stdout.write(self.style.ERROR(f"File not found: {reviews_path}"))
            return

        restaurants = list(Restaurant.objects.all().order_by("id"))
        if not restaurants:
            self.stdout.write(self.style.ERROR("No restaurants found! Import restaurants first."))
            return

        # map name -> object dan index -> object (1-based)
        name_map = {r.name.strip().lower(): r for r in restaurants if r.name}
        index_map = {i+1: r for i, r in enumerate(restaurants)}

        # ensure sample users user1..user20
        users = []
        for i in range(1, 21):
            u, _ = User.objects.get_or_create(username=f"user{i}", defaults={"email": f"user{i}@example.com"})
            users.append(u)

        f, dialect = open_csv(reviews_path)
        reader = csv.DictReader(f, dialect=dialect)

        imported, skipped = 0, 0

        for row in reader:
            # user
            try:
                # pakai user_id kalau ada, jika tidak: sebar round-robin
                uid = row.get("user_id", "").strip()
                if uid:
                    uid_i = int(float(uid))
                    user = users[(uid_i - 1) % len(users)]
                else:
                    # deterministic: pakai hash review_text
                    h = abs(hash(row.get("review_text",""))) % len(users)
                    user = users[h]
            except Exception:
                user = users[0]

            # restaurant
            restaurant = None
            rid = (row.get("restaurant_id") or "").strip()
            rname = (row.get("restaurant_name") or "").strip().lower()

            if rid:
                try:
                    restaurant = index_map[int(float(rid))]
                except Exception:
                    restaurant = None
            if not restaurant and rname:
                restaurant = name_map.get(rname)

            if not restaurant:
                skipped += 1
                continue

            # rating
            try:
                rating = int(float(row.get("rating", 0)))
            except Exception:
                rating = 0
            rating = max(1, min(5, rating)) if rating else 3

            comment = row.get("review_text") or row.get("comment") or ""
            # unique_together guard
            if Review.objects.filter(user=user, restaurant=restaurant).exists():
                skipped += 1
                continue

            Review.objects.create(
                user=user,
                restaurant=restaurant,
                rating=rating,
                comment=comment[:2000],
            )
            imported += 1

        f.close()
        self.stdout.write(self.style.SUCCESS(
            f"Reviews → imported: {imported}, skipped (dupe/unmatched): {skipped}"
        ))
