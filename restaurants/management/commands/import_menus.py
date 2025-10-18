import pandas as pd
from django.core.management.base import BaseCommand
from restaurants.models import Restaurant, Menu
from django.conf import settings
import os

class Command(BaseCommand):
    help = "Import menus from Excel, split by comma per restaurant"

    def add_arguments(self, parser):
        parser.add_argument("--file", type=str, default="data/Menus.xlsx")
        parser.add_argument("--truncate", action="store_true")
        parser.add_argument("--debug", action="store_true")

    def handle(self, *args, **options):
        file_path = options["file"]
        truncate = options["truncate"]
        debug = options["debug"]

        # truncate jika diminta
        if truncate:
            self.stdout.write("Menghapus semua data Menu...")
            Menu.objects.all().delete()

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"File tidak ditemukan: {file_path}"))
            return

        df = pd.read_excel(file_path)
        df.columns = [c.strip().lower() for c in df.columns]

        if not all(c in df.columns for c in ["resto_id", "resto_name", "list menu"]):
            self.stdout.write(self.style.ERROR("Kolom wajib: resto_id, resto_name, list menu"))
            return

        count = 0
        for _, row in df.iterrows():
            resto_id = row["resto_id"]
            resto_name = str(row["resto_name"]).strip()
            menu_list = str(row["list menu"]).strip()

            # skip jika kosong
            if not resto_id or not menu_list or menu_list.lower() == "nan":
                continue

            try:
                resto = Restaurant.objects.get(id=resto_id)
            except Restaurant.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"Restoran ID {resto_id} tidak ditemukan"))
                continue

            # Pisahkan menu berdasarkan koma
            menus = [m.strip() for m in menu_list.split(",") if m.strip()]
            for menu_name in menus:
                Menu.objects.create(
                    restaurant=resto,
                    name=menu_name,
                    price=None  # boleh kosong
                )
                count += 1
                if debug:
                    self.stdout.write(f"Tambah menu: {menu_name} ({resto_name})")

        self.stdout.write(self.style.SUCCESS(f"Berhasil import {count} menu."))
