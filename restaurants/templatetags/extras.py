from django import template
import json

register = template.Library()

@register.filter
def get_item(obj, key):
    """
    Ambil item dari:
    - dict: dukung kunci int/string ("1" atau 1)
    - list/tuple: dukung index 1-based (1..len) dan 0-based (0..len-1)
    - string: kalau string JSON yang berisi dict/list, parse dulu
    Selalu mengembalikan 0 kalau tidak ketemu/invalid agar aman di template.
    """
    if obj is None:
        return 0

    # Jika string, coba parse JSON (misal hasil json.dumps)
    if isinstance(obj, str):
        try:
            obj = json.loads(obj)
        except Exception:
            return 0

    # Normalisasi kunci
    try:
        ikey = int(key)
    except (ValueError, TypeError):
        ikey = key  # biarkan string kalau memang bukan angka

    # List/Tuple
    if isinstance(obj, (list, tuple)):
        if isinstance(ikey, int):
            # Coba 1-based (1..len)
            if 1 <= ikey <= len(obj):
                return obj[ikey - 1]
            # fallback 0-based
            if 0 <= ikey < len(obj):
                return obj[ikey]
        return 0

    # Dict
    if isinstance(obj, dict):
        if ikey in obj:
            return obj[ikey]
        # kunci mungkin diserialisasi sebagai string
        if isinstance(ikey, int) and str(ikey) in obj:
            return obj[str(ikey)]
        return 0

    return 0

@register.filter
def to_int(value):
    try:
        return int(value)
    except Exception:
        return 0

@register.filter
def percent(part, total):
    try:
        part = float(part or 0)
        total = float(total or 0)
        if total == 0:
            return 0
        return (part / total) * 100
    except Exception:
        return 0
