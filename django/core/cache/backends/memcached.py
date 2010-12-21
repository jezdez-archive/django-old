"Memcached cache backend"

import time
from threading import local

from django.core.cache.backends.base import BaseCache, InvalidCacheBackendError
from django.utils import importlib

class CacheClass(BaseCache):
    def __init__(self, server, params):
        BaseCache.__init__(self, params)
        self._local = local()
        if isinstance(server, basestring):
            self._servers = server.split(';')
        else:
            self._servers = server

        # The exception type to catch from the underlying library for a key
        # that was not found. This is a ValueError for python-memcache,
        # pylibmc.NotFound for pylibmc, and cmemcache will return None without
        # raising an exception.
        self.LibraryValueNotFoundException = ValueError

        binding = params.get('BINDING', None)
        if binding:
            memcache = importlib.import_module(binding)
            if hasattr(memcache, 'NotFound'):
                self.LibraryValueNotFoundException = memcache.NotFound
        else:
            try:
                import cmemcache as memcache
                import warnings
                warnings.warn(
                    "Support for the 'cmemcache' library has been deprecated. Please use python-memcached or pyblimc instead.",
                    DeprecationWarning
                )
            except ImportError:
                try:
                    import memcache
                except:
                    raise InvalidCacheBackendError(
                        "Memcached cache backend requires either the 'memcache,' 'pylibmc,' or 'cmemcache' library"
                    )
        self._options = params.get('OPTIONS', None)
        self._lib = memcache

    @property
    def _cache(self):
        """
        Implements transparent thread-safe access to a memcached client.
        """
        client = getattr(self._local, 'client', None)
        if client:
            return client

        client = self._lib.Client(self._servers)

        if hasattr(client, 'behaviors') and self._options:
            client.behaviors = self._options

        self._local.client = client
        return client

    def _get_memcache_timeout(self, timeout):
        """
        Memcached deals with long (> 30 days) timeouts in a special
        way. Call this function to obtain a safe value for your timeout.
        """
        timeout = timeout or self.default_timeout
        if timeout > 2592000: # 60*60*24*30, 30 days
            # See http://code.google.com/p/memcached/wiki/FAQ
            # "You can set expire times up to 30 days in the future. After that
            # memcached interprets it as a date, and will expire the item after
            # said date. This is a simple (but obscure) mechanic."
            #
            # This means that we have to switch to absolute timestamps.
            timeout += int(time.time())
        return timeout

    def add(self, key, value, timeout=0, version=None):
        key = self.make_key(key, version=version)
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        return self._cache.add(key, value, self._get_memcache_timeout(timeout))

    def get(self, key, default=None, version=None):
        key = self.make_key(key, version=version)
        val = self._cache.get(key)
        if val is None:
            return default
        return val

    def set(self, key, value, timeout=0, version=None):
        key = self.make_key(key, version=version)
        self._cache.set(key, value, self._get_memcache_timeout(timeout))

    def delete(self, key, version=None):
        key = self.make_key(key, version=version)
        self._cache.delete(key)

    def get_many(self, keys, version=None):
        new_keys = map(lambda x: self.make_key(x, version=version), keys)
        ret = self._cache.get_multi(new_keys)
        if ret:
            _ = {}
            m = dict(zip(new_keys, keys))
            for k, v in ret.items():
                _[m[k]] = v
            ret = _
        return ret

    def close(self, **kwargs):
        self._cache.disconnect_all()

    def incr(self, key, delta=1, version=None):
        key = self.make_key(key, version=version)
        try:
            val = self._cache.incr(key, delta)

        # python-memcache responds to incr on non-existent keys by
        # raising a ValueError, pylibmc by raising a pylibmc.NotFound
        # and Cmemcache returns None. In all cases,
        # we should raise a ValueError though.
        except self.LibraryValueNotFoundException:
            val = None
        if val is None:
            raise ValueError("Key '%s' not found" % key)
        return val

    def decr(self, key, delta=1, version=None):
        key = self.make_key(key, version=version)
        try:
            val = self._cache.decr(key, delta)

        # python-memcache responds to incr on non-existent keys by
        # raising a ValueError, pylibmc by raising a pylibmc.NotFound
        # and Cmemcache returns None. In all cases,
        # we should raise a ValueError though.
        except self.LibraryValueNotFoundException:
            val = None
        if val is None:
            raise ValueError("Key '%s' not found" % key)
        return val

    def set_many(self, data, timeout=0, version=None):
        safe_data = {}
        for key, value in data.items():
            key = self.make_key(key, version=version)
            if isinstance(value, unicode):
                value = value.encode('utf-8')
            safe_data[key] = value
        self._cache.set_multi(safe_data, self._get_memcache_timeout(timeout))

    def delete_many(self, keys, version=None):
        l = lambda x: self.make_key(x, version=version)
        self._cache.delete_multi(map(l, keys))

    def clear(self):
        self._cache.flush_all()
