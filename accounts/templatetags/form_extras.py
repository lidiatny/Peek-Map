# accounts/templatetags/form_extras.py
from django import template

register = template.Library()

@register.filter
def add_class(field, css_class):
    return field.as_widget(attrs={
        "class": f"{field.css_classes()} {css_class}"
    })