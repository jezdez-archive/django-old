from django import template
from django.contrib.staticfiles import storage

register = template.Library()


@register.simple_tag
def static(path):
    """
    A template tag that returns the URL to a file
    using staticfiles' storage backend
    """
    return storage.configured_storage.url(path)
