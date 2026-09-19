from django import template
register = template.Library()

@register.filter
def attr(obj, field_name):
    if obj is None:
        return ''
    for parte in str(field_name).replace('__', '.').split('.'):
        obj = getattr(obj, parte, None)
        if obj is None:
            break
    return obj
