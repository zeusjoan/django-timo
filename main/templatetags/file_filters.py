from django import template

register = template.Library()

@register.filter
def is_pdf(value):
    if not value:
        return False
    return value.name.lower().endswith('.pdf')
