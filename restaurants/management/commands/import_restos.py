# restaurants/management/commands/import_restos.py
import os, math, csv, json
from django.core.management.base import BaseCommand
from django.db import transaction, connection
from django.conf import settings
from restaurants.models import Restaurant

# ---------- utils ----------
def read_table(path):
    import pandas as pd
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xls"):
        return pd.read_excel(path)  # butuh openpyxl utk .xlsx
    # CSV fallback (auto-deteksi delimiter & encoding)
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        for sep in (None, ",", ";", "\t", "|"):
            try:
                df = pd.read_csv(path, encoding=enc, sep=sep, engine="python",
                                 on_bad_lines="skip", quoting=csv.QUOTE_MINIMAL)
                if len(df) > 0 and len(df.columns) >= 2:
                    return df
            except Exception:
                continue
    raise RuntimeError("Gagal membaca file Restaurants. Gunakan .xlsx untuk paling aman.")

def to_float(x):
    try:
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return None
        s = str(x).strip().replace(",", ".")
        return float(s)
    except Exception:
        return None

def clean_text(s):
    if s is None: return ""
    s = str(s).replace('""', '"').strip()
    return "" if s == "-" else s

def pick(cols, *cands):
    """
    Pilih nama kolom yang ada dari daftar kandidat (case-insensitive).
    Return: nama kolom sesuai di df.columns atau None.
    """
    norm = {str(c).lower().strip(): c for c in cols}
    for cand in cands:
        key = str(cand).lower().strip()
        if key in norm:
            return norm[key]
    return None

# ---------- command ----------
class Command(BaseCommand):
    help = "Truncate (opsional) & import ulang Restaurants dari XLSX/CSV. "\
           "Menyimpan mapping resto_id→db_id ke data/_resto_id_map.json."

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="Path ke data/Restaurants.xlsx (atau .csv).")
        parser.add_argument("--truncate", action="store_true", help="Hapus semua Restaurant sebelum import.")
        parser.add_argument("--reset-pk", dest="reset_pk", action="store_true",
                            help="Reset autoincrement PK (SQLite/Postgres).")

    @transaction.atomic
    def handle(self, *args, **opts):
        path = opts["file"]
        if not os.path.exists(path):
            self.stderr.write(self.style.ERROR(f"File not found: {path}"))
            return

        if opts.get("truncate"):
            self.stdout.write(self.style.WARNING("Truncating Restaurant table..."))
            Restaurant.objects.all().delete()
            if opts.get("reset_pk"):
                self._reset_pk()

        # read
        df = read_table(path)
        cols = df.columns

        # ---- mapping kolom sesuai sheet kamu ----
        # (lihat screenshot: resto_id, resto_name, type, city, keywords, longitude, latitude, price_range, list menu, review_count)
        restoid_col = pick(cols, "resto_id", "restaurant_id", "id")
        name_col    = pick(cols, "resto_name", "name", "restaurant_name")
        type_col    = pick(cols, "type", "cuisine_type")
        city_col    = pick(cols, "city", "kota")
        keywords_col= pick(cols, "keywords")
        lng_col     = pick(cols, "longitude", "lng", "long")
        lat_col     = pick(cols, "latitude", "lat")
        pr_col      = pick(cols, "price_range", "price range")
        menulist_col= pick(cols, "list menu", "menu_list")
        rcnt_col    = pick(cols, "review_count", "reviews_count")

        if not name_col:
            raise SystemExit("Kolom nama restoran tidak ditemukan (cari: resto_name/name/restaurant_name).")

        created = 0
        updated = 0
        skipped = 0
        id_map = {}  # resto_id (file) -> Restaurant.id

        for _, row in df.iterrows():
            name = clean_text(row.get(name_col))
            if not name:
                skipped += 1
                continue

            cuisine_type = clean_text(row.get(type_col)) if type_col else ""
            city         = clean_text(row.get(city_col)) if city_col else ""
            keywords     = clean_text(row.get(keywords_col)) if keywords_col else ""
            price_range  = clean_text(row.get(pr_col)) if pr_col else ""
            menu_list    = clean_text(row.get(menulist_col)) if menulist_col else ""
            review_count = row.get(rcnt_col)
            try:
                review_count = int(float(review_count)) if review_count not in (None, "", "-") else 0
            except Exception:
                review_count = 0

            longitude = to_float(row.get(lng_col)) if lng_col else None
            latitude  = to_float(row.get(lat_col)) if lat_col else None

            external_id = None
            if restoid_col:
                raw_rid = row.get(restoid_col)
                if raw_rid not in (None, ""):
                    try:
                        external_id = str(int(float(raw_rid)))
                    except Exception:
                        external_id = str(raw_rid).strip()

            # upsert by external_id (kalau ada), else by (name, city)
            lookup = {"external_id": external_id} if external_id else {"name": name, "city": city or None}

            obj, is_created = Restaurant.objects.update_or_create(
                **lookup,
                defaults={
                    "name": name,
                    "cuisine_type": cuisine_type or None,  # db_column='type'
                    "address": city or None,
                    "keywords": keywords or None,
                    "price_range": price_range or None,
                    "menu_list": menu_list or None,
                    "review_count": review_count,
                    "longitude": longitude,
                    "latitude": latitude,
                    # JANGAN isi average_rating (property). Kalau mau, isi ke field 'rating':
                    # "rating": to_float(row.get("rating"))  # jika ada kolom rating terpisah
                }
            )
            created += 1 if is_created else 0
            updated += 0 if is_created else 1

            if external_id:
                id_map[external_id] = obj.id

        # save mapping
        map_path = os.path.join(settings.BASE_DIR, "data", "_resto_id_map.json")
        os.makedirs(os.path.dirname(map_path), exist_ok=True)
        with open(map_path, "w", encoding="utf-8") as f:
            json.dump(id_map, f, ensure_ascii=False, indent=2)

        self.stdout.write(self.style.SUCCESS(
            f"Selesai import. Created: {created}, Updated: {updated}, Skipped: {skipped}"
        ))
        self.stdout.write(self.style.SUCCESS(f"Mapping saved → {map_path} (keys={len(id_map)})"))

    def _reset_pk(self):
        vendor = connection.vendor
        with connection.cursor() as cur:
            if vendor == "sqlite":
                cur.execute("DELETE FROM sqlite_sequence WHERE name='restaurant'")
            elif vendor == "postgresql":
                # ganti nama sequence kalau berbeda
                cur.execute("ALTER SEQUENCE restaurant_id_seq RESTART WITH 1")
