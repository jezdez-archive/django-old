import hashlib
import os
import re

from django.conf import settings
from django.core.cache import get_cache, InvalidCacheBackendError, cache as default_cache
from django.core.exceptions import ImproperlyConfigured, SuspiciousOperation
from django.core.files.storage import FileSystemStorage, get_storage_class
from django.core.files.base import ContentFile
from django.template import Template, Context
from django.utils.importlib import import_module
from django.utils.encoding import force_unicode
from django.utils.functional import LazyObject

from django.contrib.staticfiles.utils import check_settings


urltag_re = re.compile(r"""
url\(
  (\s*)                 # allow whitespace wrapping (and capture)
  (                     # capture actual url
    [^\)\\\r\n]*?           # don't allow newlines, closing paran, escape chars (1)
    (?:\\.                  # process all escapes here instead
        [^\)\\\r\n]*?           # proceed, with previous restrictions (1)
    )*                     # repeat until end
  )
  (\s*)                 # whitespace again (and capture)
\)
""", re.VERBOSE)


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
        check_settings()
        super(StaticFilesStorage, self).__init__(location, base_url, *args, **kwargs)


class CacheBustingMixin(object):

    def __init__(self, *args, **kwargs):
        super(CacheBustingMixin, self).__init__(*args, **kwargs)
        self.saved_files = []
        try:
            self.cache = get_cache('staticfiles')
        except InvalidCacheBackendError:
            # Use the default backend
            self.cache = default_cache

    def hash_name(self, name, content=None):
        if content is None:
            if not self.exists(name):
                raise SuspiciousOperation("Attempted access to '%s' denied." % name)
            content = self.open(self.path(name))
        path, filename = os.path.split(name)
        root, ext = os.path.splitext(filename)
        # Get the MD5 hash of the file
        md5 = hashlib.md5()
        for chunk in content.chunks():
            md5.update(chunk)
        md5sum = md5.hexdigest()[:12]
        return os.path.join(path, u"%s.%s%s" % (root, md5sum, ext))

    def cache_key(self, name):
        return 'staticfiles:cache:%s' % name

    def url(self, name):
        cache_key = self.cache_key(name)
        hashed_name = self.cache.get(cache_key, self.hash_name(name))
        return super(CacheBustingMixin, self).url(hashed_name)

    def save(self, name, content):
        original_name = super(CacheBustingMixin, self).save(name, content)
        hashed_name = self.hash_name(original_name, content)
        # Return the name if the file is already there
        if os.path.exists(hashed_name):
            return hashed_name
        # Save the file
        rendered_content = Template(content.read()).render(Context({}))
        hashed_name = self._save(hashed_name, ContentFile(rendered_content))
        # Use filenames with forward slashes, even on Windows
        hashed_name = force_unicode(hashed_name.replace('\\', '/'))
        self.cache.set(self.cache_key(name), hashed_name)
        self.saved_files.append((name, hashed_name))
        return hashed_name

    def url_converter(self, name):
        """
        Normalize the URL
        """
        def converter(matchobj):
            url = matchobj.groups()[1]
            if url[:1] in '"\'':
                url = url[1:]
            if url[-1:] in '"\'':
                url = url[:-1]
            level = url.count(os.pardir)
            if level:
                url_parts = name.split('/')[:-level-1] + url.split('/')[level:]
                url = self.url('/'.join(url_parts))
            return "url('%s')" % url
        return converter

    def path_level(self, (name, hashed_name)):
        return len(name.split(os.sep))

    def delete_cache(self, paths):
        self.cache.delete_many([self.cache_key(path) for path in paths])

    def post_process(self, paths):
        """
        Post process method called by the collectstatic management command.
        """
        self.delete_cache(paths)
        for original_name, hashed_name in sorted(
                self.saved_files, key=self.path_level, reverse=True):
            original = self.open(original_name)
            converted_content = urltag_re.sub(
                self.url_converter(original_name), original.read())
            with open(self.path(hashed_name), 'w') as hashed_file:
                hashed_file.write(converted_content)

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



class ConfiguredStorage(LazyObject):
    def _setup(self):
        self._wrapped = get_storage_class(settings.STATICFILES_STORAGE)()

configured_storage = ConfiguredStorage()
