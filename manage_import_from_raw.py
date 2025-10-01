# manage_import_from_raw.py
import os, csv, sys, django
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")  # ← adjust if your settings module differs

django.setup()

from restaurants.models import Restaurant
from reviews.models import Review
from django.contrib.auth.models import User

import pandas as pd
import numpy as np

RAW_RESTOS = BASE_DIR / "data" / "All_Restaurant_Data - Sheet1.csv"
RAW_REVIEWS = BASE_DIR / "data" / "All_Review_Data - Sheet1.csv"

def main():
    # Load restaurants and clean columns
    r_df = pd.read_csv(RAW_RESTOS)
    r_df["resto_id"] = pd.to_numeric(r_df["resto_id"], errors="coerce")
    r_df = r_df.dropna(subset=["resto_id"]).copy()
    r_df["resto_id"] = r_df["resto_id"].astype(int)

    # Build normalized fields
    name = r_df["resto_name"].astype(str).str.strip()
    lat = pd.to_numeric(r_df.get("latitude"), errors="coerce")
    lng = pd.to_numeric(r_df.get("langitude"), errors="coerce")  # note: 'langitude' in your CSV
    desc = r_df.get("keywords", pd.Series([""]*len(r_df))).astype(str)

    # Create restaurants in sorted order of resto_id
    r_df = r_df.assign(_name=name, _lat=lat, _lng=lng, _desc=desc).sort_values("resto_id")
    resto_id_to_pk = {}

    print(f"Importing {len(r_df)} restaurants…")
    for _, row in r_df.iterrows():
        obj, _ = Restaurant.objects.get_or_create(
            name=row["_name"],
            defaults={
                "address": "",
                "latitude": row["_lat"] if not pd.isna(row["_lat"]) else None,
                "longitude": row["_lng"] if not pd.isna(row["_lng"]) else None,
                "rating": None,
                "description": row["_desc"] if row["_desc"] != "nan" else "",
            },
        )
        resto_id_to_pk[int(row["resto_id"])] = obj.pk

    # Prepare 20 synthetic users (if missing)
    users = []
    for i in range(1, 21):
        u, _ = User.objects.get_or_create(username=f"user{i}", defaults={"email": f"user{i}@example.com"})
        users.append(u)

    # Load reviews
    v_df = pd.read_csv(RAW_REVIEWS)
    v_df["resto_id"] = pd.to_numeric(v_df["resto_id"], errors="coerce")
    v_df = v_df.dropna(subset=["resto_id"]).copy()
    v_df["resto_id"] = v_df["resto_id"].astype(int)
    v_df["rating"] = pd.to_numeric(v_df["rating"], errors="coerce").clip(1,5)

    # Assign user ids 1..20 if missing
    if "user_id" not in v_df.columns:
        v_df["user_id"] = np.nan

    v_df = v_df.sort_values(["resto_id", "review_id"])
    # deterministic round-robin 1..20 for NaN users
    rr = ((pd.Series(range(len(v_df))) % 20) + 1).astype(int)
    v_df.loc[v_df["user_id"].isna(), "user_id"] = rr[v_df["user_id"].isna()].values
    v_df["user_id"] = pd.to_numeric(v_df["user_id"], errors="coerce").fillna(1).astype(int)
    v_df["user_id"] = ((v_df["user_id"] - 1) % 20) + 1  # clamp to 1..20

    # Create Review rows (skip duplicates per your unique_together)
    created = 0
    skipped = 0
    for _, row in v_df.iterrows():
        rest_pk = resto_id_to_pk.get(int(row["resto_id"]))
        if not rest_pk or pd.isna(row["rating"]):
            continue
        user = users[int(row["user_id"]) - 1]
        try:
            Review.objects.create(
                user=user,
                restaurant_id=rest_pk,
                rating=int(row["rating"]),
                comment=str(row.get("review_text", "") or "")[:2000],
            )
            created += 1
        except Exception:
            skipped += 1

    print(f"Done. Reviews created: {created}, skipped: {skipped}")

if __name__ == "__main__":
    main()