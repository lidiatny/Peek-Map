# restaurants/management/commands/import_restos.py
import csv
from django.core.management.base import BaseCommand
from restaurants.models import Restaurant

def open_csv(path):
    # handle BOM & delimiter ; or ,
    f = open(path, 'r', encoding='utf-8-sig', newline='')
    sample = f.read(4096)
    f.seek(0)
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=',;')
    except Exception:
        dialect = csv.excel
    return f, dialect

class Command(BaseCommand):
    help = "Import restaurants from a CSV file (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str, help="Path to CSV file")

    def handle(self, *args, **options):
        path = options["csv_file"]
        f, dialect = open_csv(path)
        reader = csv.DictReader(f, dialect=dialect)

        created, updated, skipped = 0, 0, 0

        for row in reader:
            # map fleksibel
            name = (row.get("name") or row.get("resto_name") or "").strip()
            if not name:
                self.stdout.write(self.style.WARNING(f"Skip: name kosong pada row {row}"))
                skipped += 1
                continue

            # kolom opsional
            address = (row.get("address") or "").strip()
            lat_raw = (row.get("latitude") or "").strip()
            lng_raw = (row.get("longitude") or row.get("langitude") or "").strip()
            rating_raw = (row.get("rating") or "").strip()
            description = (row.get("description") or row.get("keywords") or "").strip()

            def to_float(x):
                if not x:
                    return None
                try:
                    return float(x)
                except ValueError:
                    # handle format " -6.2" atau " -6200000" (gaya scrapper)
                    x2 = x.replace('.', '')
                    try:
                        return float(x2) / 1_000_000
                    except Exception:
                        return None

            latitude = to_float(lat_raw)
            longitude = to_float(lng_raw)
            try:
                rating = float(rating_raw) if rating_raw else None
            except Exception:
                rating = None

            obj, created_flag = Restaurant.objects.update_or_create(
                name=name,
                defaults={
                    "address": address,
                    "latitude": latitude,
                    "longitude": longitude,
                    "rating": rating,
                    "description": description,
                }
            )
            if created_flag:
                created += 1
            else:
                updated += 1

        f.close()
        self.stdout.write(self.style.SUCCESS(
            f"Restaurants → created: {created}, updated: {updated}, skipped (no name): {skipped}"
        ))
