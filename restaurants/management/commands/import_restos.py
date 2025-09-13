import csv
from django.core.management.base import BaseCommand
from restaurants.models import Restaurant   # ✅ pakai model asli

class Command(BaseCommand):
    help = "Import restaurants from a CSV file"

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str, help="Path to CSV file")

    def handle(self, *args, **options):
        csv_file = options["csv_file"]

        with open(csv_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                try:
                    Restaurant.objects.create(
                        name=row.get("name", "Unknown"),
                        address=row.get("address", ""),
                        latitude=float(row["latitude"]) if row.get("latitude") else None,
                        longitude=float(row["longitude"]) if row.get("longitude") else None,
                        rating=float(row["rating"]) if row.get("rating") else None,
                        description=row.get("description", ""),
                    )
                    count += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"❌ Error on row {row}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"✅ Imported {count} restaurants"))
