from django import template
from django.conf import settings
from django.core.files.storage import get_storage_class

register = template.Library()

storage = get_storage_class(settings.STATICFILES_STORAGE)()


@register.simple_tag
def static(path):
    """
    A template tag that returns the URL to a file
    using staticfiles' storage backend
    """
    if storage.exists(path):
        return storage.url(path)
    return ''
