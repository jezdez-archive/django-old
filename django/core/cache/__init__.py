"""
Caching framework.

This package defines set of cache backends that all conform to a simple API.
In a nutshell, a cache is a set of values -- which can be any object that
may be pickled -- identified by string keys.  For the complete API, see
the abstract BaseCache class in django.core.cache.backends.base.

Client code should not access a cache backend directly; instead it should
either use the "cache" variable made available here, or it should use the
get_cache() function made available here. get_cache() takes a backend URI
(e.g. "memcached://127.0.0.1:11211/") and returns an instance of a backend
cache class.

See docs/topics/cache.txt for information on the public API.
"""

try:
    # The mod_python version is more efficient, so try importing it first.
    from mod_python.util import parse_qsl
except ImportError:
    try:
        # Python 2.6 and greater
        from urlparse import parse_qsl
    except ImportError:
        # Python 2.5, 2.4.  Works on Python 2.6 but raises
        # PendingDeprecationWarning
        from cgi import parse_qsl

from django.conf import settings
from django.core import signals
from django.core.cache.backends.base import InvalidCacheBackendError, CacheKeyWarning
from django.utils import importlib

# Name for use in settings file --> name of module in "backends" directory.
# Any backend scheme that is not in this dictionary is treated as a Python
# import path to a custom backend.
BACKENDS = {
    'memcached': 'memcached',
    'locmem': 'locmem',
    'file': 'filebased',
    'db': 'db',
    'dummy': 'dummy',
}

DEFAULT_CACHE_ALIAS = 'default'

if not settings.CACHES:
    import warnings
    warnings.warn(
        "settings.CACHE_* is deprecated; use settings.CACHES instead.",
        PendingDeprecationWarning
    )
    settings.CACHES[DEFAULT_CACHE_ALIAS] = {
        'ENGINE': 'django.core.cache.backends.locmem',
        'NAME': '',
        'OPTIONS': {},
        'VERSION': settings.CACHE_VERSION,
        'KEY_PREFIX': settings.CACHE_KEY_PREFIX,
        'KEY_FUNCTION': settings.CACHE_KEY_FUNCTION,
    }

if DEFAULT_CACHE_ALIAS not in settings.CACHES:
    raise ImproperlyConfigured("You must define a '%s' cache" % DEFAULT_CACHE_ALIAS)

def parse_backend_uri(backend_uri):
    """
    Converts the "backend_uri" into a cache scheme ('db', 'memcached', etc), a
    host and any extra params that are required for the backend. Returns a
    (scheme, host, params) tuple.
    """
    if backend_uri.find(':') == -1:
        raise InvalidCacheBackendError("Backend URI must start with scheme://")
    scheme, rest = backend_uri.split(':', 1)
    if not rest.startswith('//'):
        raise InvalidCacheBackendError("Backend URI must start with scheme://")

    host = rest[2:]
    qpos = rest.find('?')
    if qpos != -1:
        params = dict(parse_qsl(rest[qpos+1:]))
        host = rest[2:qpos]
    else:
        params = {}
    if host.endswith('/'):
        host = host[:-1]

    return scheme, host, params

def handle_key_params(key_prefix=None, version=None, key_func=None):
    """
    Helper function to handle key related cache options,
    returning a dictionary with the correct values.
    """
    if key_prefix is None:
        key_prefix = settings.CACHE_KEY_PREFIX
    if version is None:
        version = settings.CACHE_VERSION
    if key_func is None:
        key_func = settings.CACHE_KEY_FUNCTION
    if key_func is not None and not callable(key_func):
        key_func_module_path, key_func_name = key_func.rsplit('.', 1)
        key_func_module = importlib.import_module(key_func_module_path)
        key_func = getattr(key_func_module, key_func_name)
    return dict(key_prefix=key_prefix, version=version, key_func=key_func)

def get_cache(backend, key_prefix=None, version=None, key_func=None):
    key_params = handle_key_params(key_prefix, version, key_func)
    if '://' in backend:
        scheme, name, params = parse_backend_uri(backend)
        if scheme in BACKENDS:
            engine = 'django.core.cache.backends.%s' % BACKENDS[scheme]
        else:
            engine = scheme
    else:
        # Get the CACHES entry for the wanted backend
        cache_conf = settings.CACHES.get(backend, None)
        if cache_conf is None:
            InvalidCacheBackendError("Couldn't find a cache backend named '%s'" % backend)
        name, engine, params = cache_conf['NAME'], cache_conf['ENGINE'], cache_conf['OPTIONS']
        # Update the key_params from cache specific settings
        for key_param in key_params:
            if key_param == 'key_func':
                key_param = 'key_function' # even setting with param name
            if key_param.upper() in cache_conf:
                key_params[key_param] = cache_conf[key_param.upper()]
    module = importlib.import_module(engine)
    return module.CacheClass(name, params, **key_params)

cache = get_cache(DEFAULT_CACHE_ALIAS)

# Some caches -- python-memcached in particular -- need to do a cleanup at the
# end of a request cycle. If the cache provides a close() method, wire it up
# here.
if hasattr(cache, 'close'):
    signals.request_finished.connect(cache.close)
