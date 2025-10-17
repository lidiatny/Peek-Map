import os, math, csv, json
from datetime import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
from django.conf import settings
from restaurants.models import Restaurant
from reviews.models import Review
from django.utils import timezone

def read_table(path):
    import pandas as pd
    ext = os.path.splitext(path)[1].lower()
    if ext in [".xlsx", ".xls"]:
        return pd.read_excel(path)
    for enc in ["utf-8-sig", "utf-8", "latin-1"]:
        for sep in [None, ",", ";", "\t", "|"]:
            try:
                df = pd.read_csv(path, encoding=enc, sep=sep, engine="python",
                                 on_bad_lines="skip", quoting=csv.QUOTE_MINIMAL)
                if len(df) > 0 and len(df.columns) >= 2:
                    return df
            except Exception:
                continue
    raise RuntimeError("Gagal membaca file Reviews.")

def to_float(x):
    try:
        return float(str(x).strip().replace(",", "."))
    except Exception:
        return None

def parse_dt(x):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return None
    s = str(x).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            continue
    return None

def pick(cols, *cands):
    low = {str(c).lower().strip(): c for c in cols}
    for c in cands:
        if c in low: return low[c]
    return None

class Command(BaseCommand):
    help = "Import Reviews + pakai mapping data/_resto_id_map.json agar resto_id di file nyambung ke Restaurant DB."

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="Path ke Reviews.csv/.xlsx")
        parser.add_argument("--truncate", action="store_true", help="Hapus semua Review sebelum import")
        parser.add_argument("--user-prefix", default="user", help="Prefix username jika create user otomatis")

    @transaction.atomic
    def handle(self, *args, **opts):
        path = opts["file"]
        if not os.path.exists(path):
            self.stderr.write(self.style.ERROR(f"File not found: {path}"))
            return

        if opts["truncate"]:
            self.stdout.write(self.style.WARNING("Truncating Review table..."))
            Review.objects.all().delete()

        # load mapping dari import_restos
        map_path = os.path.join(settings.BASE_DIR, "data", "_resto_id_map.json")
        idmap = {}
        if os.path.exists(map_path):
            with open(map_path, "r", encoding="utf-8") as f:
                idmap = json.load(f)

        df = read_table(path)
        cols = df.columns

        rid_col  = pick(cols, "resto_id", "restaurant_id", "id_resto")
        uid_col  = pick(cols, "user_id", "username", "user")
        text_col = pick(cols, "review_text", "comment", "review")
        rate_col = pick(cols, "rating", "score", "stars")
        time_col = pick(cols, "timestamp", "created_at", "date")

        if not rid_col:
            raise SystemExit("Butuh kolom resto_id/restaurant_id pada Reviews.")

        created, skipped = 0, 0

        for _, row in df.iterrows():
            raw_rid = row.get(rid_col)
            if raw_rid in [None, ""]:
                skipped += 1
                continue

            # cari Restaurant.id di DB via mapping
            key = str(int(float(raw_rid)))
            resto_db = None
            if key in idmap:
                try:
                    resto_db = Restaurant.objects.get(id=idmap[key])
                except Restaurant.DoesNotExist:
                    resto_db = None

            # fallback (kalau mapping kosong): coba pakai id langsung
            if resto_db is None:
                try:
                    resto_db = Restaurant.objects.get(id=int(float(raw_rid)))
                except Exception:
                    resto_db = None

            if resto_db is None:
                skipped += 1
                continue

            # user
            raw_uid = row.get(uid_col) if uid_col else None
            if raw_uid is None or str(raw_uid).strip().lower() in ["", "nan"]:
                username = "importer"
            else:
                try:
                    username = f"{opts['user_prefix']}{int(float(raw_uid))}"
                except Exception:
                    username = f"{opts['user_prefix']}{str(raw_uid).strip()}"
            user, _ = User.objects.get_or_create(username=str(username)[:150])

            rating = to_float(row.get(rate_col)) if rate_col else None
            text = str(row.get(text_col) or "").strip()
            ts = parse_dt(row.get(time_col)) if time_col else None

            if ts and timezone.is_naive(ts):
                ts = timezone.make_aware(ts)

            # Hindari duplikat review untuk kombinasi user + resto
            # Selalu buat review baru tanpa skip
            Review.objects.create(
                restaurant=resto_db,
                user=user,
                rating=rating,
                comment=text,
                created_at=ts or timezone.now()
            )
            created += 1


        self.stdout.write(self.style.SUCCESS(f"Reviews imported: created={created}, skipped={skipped}"))
