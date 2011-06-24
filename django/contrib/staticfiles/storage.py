import hashlib
import os
import uuid

from django.conf import settings
from django.core.cache import get_cache, InvalidCacheBackendError
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import FileSystemStorage
from django.template import Template, Context
from django.utils.importlib import import_module
from django.utils.baseconv import base62
from django.utils.encoding import force_unicode, filepath_to_uri

from django.contrib.staticfiles import utils

try:
    cache = get_cache('staticfiles')
except InvalidCacheBackendError:
    # Use the default backend
    from django.core.cache import cache


class StaticFilesStorage(FileSystemStorage):
    """
    Standard file system storage for static files.

    The defaults for ``location`` and ``base_url`` are
    ``STATIC_ROOT`` and ``STATIC_URL``.
    """
    def __init__(self, location=None, base_url=None, *args, **kwargs):
        if location is None:
            location = settings.STATIC_ROOT
        if base_url is None:
            base_url = settings.STATIC_URL
        if not location:
            raise ImproperlyConfigured("You're using the staticfiles app "
                "without having set the STATIC_ROOT setting.")
        # check for None since we might use a root URL (``/``)
        if base_url is None:
            raise ImproperlyConfigured("You're using the staticfiles app "
                "without having set the STATIC_URL setting.")
        utils.check_settings()
        super(StaticFilesStorage, self).__init__(location, base_url, *args, **kwargs)


class CacheBustingMixin(object):

    def get_hash_filename(self, name, content=None):
        if content is None:
            content = self.open(self.path(name))
        path, filename = os.path.split(name)
        root, ext = os.path.splitext(filename)
        # Get the MD5 hash of the file
        md5 = hashlib.md5()
        for chunk in content.chunks():
            md5.update(chunk)
        md5sum = md5.hexdigest()[:12]
        return os.path.join(path, u"%s.%s%s" % (root, md5sum, ext))

    def get_cache_key(self, name):
        return 'cachebusting:%s' % name

    def url(self, name):
        hashed_name = cache.get(
            self.get_cache_key(name), self.get_hash_filename(name))
        return super(CacheBustingMixin, self).url(hashed_name)

    def save(self, name, content):
        original_name = super(CacheBustingMixin, self).save(name, content)
        hashed_name = self.get_hash_filename(original_name, content)
        # Return the name if the file is already there
        if os.path.exists(hashed_name):
            return hashed_name
        # Save the file
        actual_content = content.read()
        rendered_content = Template(actual_content).render(Context({}))
        hashed_name = self._save(hashed_name, rendered_content)
        cache.set(self.get_cache_key(name), hashed_name)
        # Store filenames with forward slashes, even on Windows
        return force_unicode(hashed_name.replace('\\', '/'))


class CachedStaticFilesStorage(CacheBustingMixin, StaticFilesStorage):
    pass


class AppStaticStorage(FileSystemStorage):
    """
    A file system storage backend that takes an app module and works
    for the ``static`` directory of it.
    """
    prefix = None
    source_dir = 'static'

    def __init__(self, app, *args, **kwargs):
        """
        Returns a static file storage if available in the given app.
        """
        # app is the actual app module
        mod = import_module(app)
        mod_path = os.path.dirname(mod.__file__)
        location = os.path.join(mod_path, self.source_dir)
        super(AppStaticStorage, self).__init__(location, *args, **kwargs)
