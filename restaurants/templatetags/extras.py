from django import template

register = template.Library()

@register.filter
def get_item(d, key):
    if d is None:
        return None
    try:
        return d.get(int(key))
    except Exception:
        return d.get(str(key), None)

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
