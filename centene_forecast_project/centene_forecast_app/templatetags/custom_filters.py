from django import template

register = template.Library()

@register.filter
def remove_percent(value):
    return value.replace('%', '') if value else value