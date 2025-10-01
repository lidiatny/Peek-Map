# manage_raw_to_clean.py
import os, sys
import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
RAW_RESTOS = BASE_DIR / "data" / "All_Restaurant_Data.csv"
RAW_REVIEWS = BASE_DIR / "data" / "All_Review_Data.csv"
OUT_RESTOS = BASE_DIR / "data" / "restaurants.csv"
OUT_REVIEWS = BASE_DIR / "data" / "reviews.csv"

def to_float(x):
    if pd.isna(x) or x == "" or x is None:
        return np.nan
    try:
        return float(x)
    except Exception:
        # try compact format (e.g., "6200000" intended as 6.2)
        x2 = str(x).replace(".", "")
        try:
            return float(x2) / 1_000_000
        except Exception:
            return np.nan

def pick(df, candidates, fallback=None):
    """Return the first existing column as Series."""
    for c in candidates:
        if c in df.columns:
            return df[c]
    return fallback

def main():
    # --- Restaurants ---
    r = pd.read_csv(RAW_RESTOS, encoding="utf-8")
    r.columns = r.columns.str.strip().str.lower()  # normalize headers

    # name
    if "name" in r.columns:
        name_series = r["name"]
    elif "resto_name" in r.columns:
        name_series = r["resto_name"]
    else:
        name_series = r.iloc[:, 0]
    name = name_series.astype(str).str.strip()

    # latitude / longitude
    lat_series = pick(r, ["latitude"])
    lng_series = pick(r, ["longitude", "langitude"])

    latitude = pd.to_numeric(lat_series, errors="coerce") if lat_series is not None else np.nan
    longitude = pd.to_numeric(lng_series, errors="coerce") if lng_series is not None else np.nan

    # description
    desc_series = pick(r, ["description", "keywords"], fallback=pd.Series([""] * len(r)))
    description = desc_series.astype(str) if desc_series is not None else ""

    restos = pd.DataFrame({
        "name": name,
        "address": "",
        "latitude": latitude,
        "longitude": longitude,
        "rating": np.nan,
        "description": description,
    })
    restos = restos[restos["name"].str.strip() != ""].copy().reset_index(drop=True)
    restos["__restaurant_id"] = np.arange(1, len(restos) + 1)

    restos_out = restos.drop(columns="__restaurant_id")
    restos_out.to_csv(OUT_RESTOS, index=False, encoding="utf-8")
    print(f"✅ Wrote {len(restos_out)} restaurants → {OUT_RESTOS}")

    # --- Reviews ---
    v = pd.read_csv(RAW_REVIEWS, encoding="utf-8")
    v.columns = v.columns.str.strip().str.lower()

    v["rating"] = pd.to_numeric(v.get("rating"), errors="coerce").clip(1, 5)

    # build restaurant_id for reviews
    name_key_in_v = "restaurant_name" if "restaurant_name" in v.columns else ("resto_name" if "resto_name" in v.columns else None)

    if name_key_in_v:
        clean_keys = restos_out["name"].str.lower().str.strip()
        name2id = {k: i+1 for i, k in enumerate(clean_keys)}
        v["restaurant_id"] = v[name_key_in_v].astype(str).str.lower().str.strip().map(name2id)
    elif "restaurant_id" in v.columns:
        v["restaurant_id"] = pd.to_numeric(v["restaurant_id"], errors="coerce")
    elif "resto_id" in v.columns and "resto_id" in r.columns:
        r_map = r[["resto_id"]].copy()
        r_map["resto_name_key"] = name.str.lower().str.strip().values
        clean_map = pd.DataFrame({
            "restaurant_id": range(1, len(restos_out) + 1),
            "resto_name_key": restos_out["name"].str.lower().str.strip()
        })
        v = v.merge(r_map[["resto_id", "resto_name_key"]], on="resto_id", how="left")
        v = v.merge(clean_map, on="resto_name_key", how="left")
    else:
        v = v.sort_values(by=v.columns[0]).reset_index(drop=True)
        v["restaurant_id"] = (np.arange(len(v)) % len(restos_out)) + 1

    # user_id handling
    if "user_id" not in v.columns:
        v["user_id"] = np.nan
    v["user_id"] = pd.to_numeric(v["user_id"], errors="coerce")
    rr = ((pd.Series(range(len(v))) % 20) + 1).astype(int)
    v.loc[v["user_id"].isna(), "user_id"] = rr[v["user_id"].isna()].values
    v["user_id"] = v["user_id"].astype(int)
    v["user_id"] = ((v["user_id"] - 1) % 20) + 1

    reviews = pd.DataFrame({
        "user_id": v["user_id"],
        "restaurant_id": pd.to_numeric(v["restaurant_id"], errors="coerce"),
        "rating": v["rating"].fillna(3).clip(1, 5).astype(int),
        "review_text": v.get("review_text") if "review_text" in v.columns else v.get("comment", "")
    }).dropna(subset=["restaurant_id"]).astype({"restaurant_id": int})

    reviews.to_csv(OUT_REVIEWS, index=False, encoding="utf-8")
    print(f"✅ Wrote {len(reviews)} reviews → {OUT_REVIEWS}")

if __name__ == "__main__":
    main()
