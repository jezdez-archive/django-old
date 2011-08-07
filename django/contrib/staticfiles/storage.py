import hashlib
import os
import posixpath
import re

from django.conf import settings
from django.core.cache import (get_cache, InvalidCacheBackendError,
                               cache as default_cache)
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import FileSystemStorage, get_storage_class
from django.utils.encoding import force_unicode
from django.utils.functional import LazyObject
from django.utils.importlib import import_module

from django.contrib.staticfiles import utils


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
        super(StaticFilesStorage, self).__init__(location, base_url,
                                                 *args, **kwargs)


class CachedFilesMixin(object):
    cached_patterns = [
        r"""(url\(['"]{0,1}\s*(.*?)["']{0,1}\))""",
        r"""(@import\s*["']\s*(.*?)["'])""",
    ]

    def __init__(self, *args, **kwargs):
        super(CachedFilesMixin, self).__init__(*args, **kwargs)
        self.saved_files = []
        try:
            self.cache = get_cache('staticfiles')
        except InvalidCacheBackendError:
            # Use the default backend
            self.cache = default_cache
        self._cached_patterns = []
        for pattern in self.cached_patterns:
            self._cached_patterns.append(re.compile(pattern))

    def hashed_name(self, name, content=None):
        if content is None:
            if not self.exists(name):
                raise ValueError("The file '%s' could not be found using %r." %
                                 (name, self))
            try:
                content = self.open(name)
            except IOError, e:
                # Handle directory paths
                return name
        path, filename = os.path.split(name)
        root, ext = os.path.splitext(filename)
        # Get the MD5 hash of the file
        md5 = hashlib.md5()
        for chunk in content.chunks():
            md5.update(chunk)
        md5sum = md5.hexdigest()[:12]
        return os.path.join(path, u"%s.%s%s" % (root, md5sum, ext))

    def cache_key(self, name):
        return u'staticfiles:cache:%s' % name

    def url(self, name, force=False):
        """
        Returns the real URL in DEBUG mode.
        """
        if settings.DEBUG and not force:
            return super(CachedFilesMixin, self).url(name)
        cache_key = self.cache_key(name)
        hashed_name = self.cache.get(cache_key)
        if hashed_name is None:
            hashed_name = self.hashed_name(name)
        return super(CachedFilesMixin, self).url(hashed_name)

    def save(self, name, content):
        original_name = super(CachedFilesMixin, self).save(name, content)

        # Return the name if the file is already there
        hashed_name = self.hashed_name(original_name, content)
        if os.path.exists(hashed_name):
            return hashed_name

        # or save the file with the hashed name
        saved_name = self._save(hashed_name, content)

        # Use filenames with forward slashes, even on Windows
        hashed_name = force_unicode(saved_name.replace('\\', '/'))
        self.cache.set(self.cache_key(name), hashed_name)
        self.saved_files.append((name, hashed_name))
        return hashed_name

    def url_converter(self, name):
        """
        Returns the custom URL converter for the given file name.
        """
        def converter(matchobj):
            """
            Converts the matched URL depending on the parent level (`..`)
            and returns the normalized and hashed URL using the url method
            of the storage.
            """
            matched, url = matchobj.groups()
            # Completely ignore http(s) prefixed URLs
            if url.startswith(('http', 'https')):
                return matched
            name_parts = name.split('/')
            # Using posix normpath here to remove duplicates
            result = url_parts = posixpath.normpath(url).split('/')
            level = url.count('..')
            if level:
                result = name_parts[:-level-1] + url_parts[level:]
            elif name_parts[:-1]:
                result = name_parts[:-1] + url_parts[-1:]
            joined_result = '/'.join(result)
            hashed_url = self.url(joined_result, force=True)
            # Return the hashed and normalized version to the file
            return 'url("%s")' % hashed_url
        return converter

    def path_level(self, (name, hashed_name)):
        return len(name.split('/'))

    def post_process(self, paths):
        """
        Post process method called by the collectstatic management command.
        """
        self.cache.delete_many([self.cache_key(path) for path in paths])
        for name, hashed_name in sorted(
                self.saved_files, key=self.path_level, reverse=True):
            with self.open(name) as original_file:
                content = original_file.read()
                for pattern in self._cached_patterns:
                    content = pattern.sub(self.url_converter(name), content)
            with open(self.path(hashed_name), 'w') as hashed_file:
                hashed_file.write(content)


class CachedStaticFilesStorage(CachedFilesMixin, StaticFilesStorage):
    """
    A static file system storage backend which also saves
    hashed copies of the files it saves.
    """
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
