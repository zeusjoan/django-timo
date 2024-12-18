from django import template

register = template.Library()

@register.filter
def sub(value, arg):
    """Odejmuje arg od value"""
    try:
        return float(value or 0) - float(arg or 0)
    except (ValueError, TypeError):
        return 0

@register.filter
def div(value, arg):
    """Dzieli value przez arg"""
    try:
        if float(arg or 0) == 0:
            return 0
        return float(value or 0) / float(arg or 0)
    except (ValueError, TypeError):
        return 0

@register.filter
def mul(value, arg):
    """Mnoży value przez arg"""
    try:
        return float(value or 0) * float(arg or 0)
    except (ValueError, TypeError):
        return 0
