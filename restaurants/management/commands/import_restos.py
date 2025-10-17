import os, math, csv, json
from django.core.management.base import BaseCommand
from django.db import transaction
from django.conf import settings
from restaurants.models import Restaurant

def read_table(path):
    import pandas as pd
    ext = os.path.splitext(path)[1].lower()
    if ext in [".xlsx", ".xls"]:
        return pd.read_excel(path)
    # CSV fallback (kalau terpaksa)
    for enc in ["utf-8-sig", "utf-8", "latin-1"]:
        for sep in [None, ",", ";", "\t", "|"]:
            try:
                df = pd.read_csv(path, encoding=enc, sep=sep, engine="python",
                                 on_bad_lines="skip", quoting=csv.QUOTE_MINIMAL)
                if len(df) > 0 and len(df.columns) >= 2:
                    return df
            except Exception:
                continue
    raise RuntimeError("Gagal membaca file Restaurants. Pakai .xlsx agar aman ya 🙏")

def to_float(x):
    try:
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return None
        return float(str(x).strip().replace(",", "."))
    except Exception:
        return None

def pick(cols, *cands):
    low = {str(c).lower().strip(): c for c in cols}
    for c in cands:
        if c in low: return low[c]
    return None

def clean_text(s):
    if s is None: return ""
    s = str(s).replace('""', '"').strip()
    return s if s != "-" else ""

class Command(BaseCommand):
    help = "Import/overwrite Restaurants dari CSV/Excel + tulis mapping resto_id→db_id ke data/_resto_id_map.json"

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="Path ke Restaurants.xlsx/.csv")
        parser.add_argument("--truncate", action="store_true", help="Hapus semua Restaurant sebelum import")

    @transaction.atomic
    def handle(self, *args, **opts):
        path = opts["file"]
        if not os.path.exists(path):
            self.stderr.write(self.style.ERROR(f"File not found: {path}"))
            return

        if opts["truncate"]:
            self.stdout.write(self.style.WARNING("Truncating Restaurant table..."))
            Restaurant.objects.all().delete()

        df = read_table(path)
        cols = df.columns

        # kolom umum di dataset kamu
        restoid_col = pick(cols, "resto_id", "restaurant_id", "id")
        name_col    = pick(cols, "resto_name", "name", "restaurant_name")
        addr_col    = pick(cols, "address", "alamat", "city", "kota")
        lat_col     = pick(cols, "latitude", "lat")
        lng_col     = pick(cols, "longitude", "lng", "long")
        rate_col    = pick(cols, "rating", "average_rating", "rating rata-rata", "rating_rata-rata")

        if not name_col:
            raise SystemExit("Kolom nama restoran tidak ditemukan (cari: resto_name/name/restaurant_name).")

        mapping = {}  # resto_id (file) -> Restaurant.id (DB)
        created = 0

        for _, row in df.iterrows():
            name = clean_text(row.get(name_col))
            if not name:
                continue

            address = clean_text(row.get(addr_col)) if addr_col else ""
            lat = to_float(row.get(lat_col)) if lat_col else None
            lng = to_float(row.get(lng_col)) if lng_col else None
            rating = to_float(row.get(rate_col)) if rate_col else None

            r = Restaurant(name=name)
            if hasattr(r, "address"):   r.address = address
            if hasattr(r, "latitude"):  r.latitude = lat
            if hasattr(r, "longitude"): r.longitude = lng
            if rating is not None and hasattr(r, "average_rating"):
                r.average_rating = rating

            r.save()
            created += 1

            # simpan mapping resto_id -> db_id jika kolomnya ada
            if restoid_col:
                file_rid = row.get(restoid_col)
                if file_rid not in [None, ""]:
                    mapping[str(int(float(file_rid)))] = r.id  # normalisasi ke string int

        # tulis mapping ke data/_resto_id_map.json
        map_path = os.path.join(settings.BASE_DIR, "data", "_resto_id_map.json")
        os.makedirs(os.path.dirname(map_path), exist_ok=True)
        with open(map_path, "w", encoding="utf-8") as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)

        self.stdout.write(self.style.SUCCESS(f"Restaurants imported: {created}"))
        self.stdout.write(self.style.SUCCESS(f"Mapping saved: {map_path} (keys={len(mapping)})"))
