"""
Functions for creating and restoring url-safe signed JSON objects.

The format used looks like this:

>>> signed.dumps("hello")
'ImhlbGxvIg.RjVSUCt6S64WBilMYxG89-l0OA8'

There are two components here, separatad by a '.'. The first component is a
URLsafe base64 encoded JSON of the object passed to dumps(). The second
component is a base64 encoded hmac/SHA1 hash of "$first_component.$secret"

signed.loads(s) checks the signature and returns the deserialised object.
If the signature fails, a BadSignature exception is raised.

>>> signed.loads("ImhlbGxvIg.RjVSUCt6S64WBilMYxG89-l0OA8")
u'hello'
>>> signed.loads("ImhlbGxvIg.RjVSUCt6S64WBilMYxG89-l0OA8-modified")
...
BadSignature: Signature failed: RjVSUCt6S64WBilMYxG89-l0OA8-modified

You can optionally compress the JSON prior to base64 encoding it to save
space, using the compress=True argument. This checks if compression actually
helps and only applies compression if the result is a shorter string:

>>> signed.dumps(range(1, 20), compress=True)
'.eJwFwcERACAIwLCF-rCiILN47r-GyZVJsNgkxaFxoDgxcOHGxMKD_T7vhAml.oFq6lAAEbkHXBHfGnVX7Qx6NlZ8'

The fact that the string is compressed is signalled by the prefixed '.' at the
start of the base64 JSON.

There are 65 url-safe characters: the 64 used by url-safe base64 and the '.'.
These functions make use of all of them.
"""
import hmac
import base64
import time

from django.conf import settings
from django.utils.hashcompat import sha_constructor
from django.utils import baseconv, simplejson
from django.utils.crypto import constant_time_compare
from django.utils.encoding import force_unicode, smart_str
from django.utils.importlib import import_module

class BadSignature(Exception):
    """
    Signature does not match
    """
    pass


class SignatureExpired(BadSignature):
    """
    Signature timestamp is older than required max_age
    """
    pass


def b64_encode(s):
    return base64.urlsafe_b64encode(s).strip('=')


def b64_decode(s):
    pad = '=' * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def base64_hmac(value, key):
    return b64_encode((hmac.new(key, value, sha_constructor).digest()))


def get_cookie_signer():
    modpath = settings.SIGNING_BACKEND
    module, attr = modpath.rsplit('.', 1)
    try:
        mod = import_module(module)
    except ImportError, e:
        raise ImproperlyConfigured(
            'Error importing cookie signer %s: "%s"' % (modpath, e))
    try:
        Signer = getattr(mod, attr)
    except AttributeError, e:
        raise ImproperlyConfigured(
            'Error importing cookie signer %s: "%s"' % (modpath, e))
    return Signer('django.http.cookies' + settings.SECRET_KEY)


def dumps(obj, key=None, salt='', compress=False):
    """
    Returns URL-safe, sha1 signed base64 compressed JSON string. If key is
    None, settings.SECRET_KEY is used instead.

    If compress is True (not the default) checks if compressing using zlib can
    save some space. Prepends a '.' to signify compression. This is included
    in the signature, to protect against zip bombs.

    salt can be used to further salt the hash, in case you're worried
    that the NSA might try to brute-force your SHA-1 protected secret.
    """
    json = simplejson.dumps(obj, separators=(',', ':'))

    # Flag for if it's been compressed or not
    is_compressed = False

    if compress:
        # Avoid zlib dependency unless compress is being used
        import zlib
        compressed = zlib.compress(json)
        if len(compressed) < (len(json) - 1):
            json = compressed
            is_compressed = True
    base64d = b64_encode(json)
    if is_compressed:
        base64d = '.' + base64d
    return TimestampSigner(key).sign(base64d, salt=salt)


def loads(s, key=None, salt='', max_age=None):
    """
    Reverse of dumps(), raises BadSignature if signature fails
    """
    base64d = smart_str(
        TimestampSigner(key).unsign(s, salt=salt, max_age=max_age))
    decompress = False
    if base64d[0] == '.':
        # It's compressed; uncompress it first
        base64d = base64d[1:]
        decompress = True
    json = b64_decode(base64d)
    if decompress:
        import zlib
        jsond = zlib.decompress(json)
    return simplejson.loads(json)


class Signer(object):
    def __init__(self, key=None, sep=':'):
        self.sep = sep
        self.key = key or settings.SECRET_KEY

    def signature(self, value, salt=''):
        # Derive a new key from the SECRET_KEY, using the optional salt
        key = sha_constructor(salt + 'signer' + self.key).hexdigest()
        return base64_hmac(value, key)

    def sign(self, value, salt=''):
        value = smart_str(value)
        return '%s%s%s' % (value, self.sep, self.signature(value, salt=salt))

    def unsign(self, signed_value, salt=''):
        signed_value = smart_str(signed_value)
        if not self.sep in signed_value:
            raise BadSignature('No "%s" found in value' % self.sep)
        value, sig = signed_value.rsplit(self.sep, 1)
        expected = self.signature(value, salt=salt)
        if constant_time_compare(sig, expected):
            return force_unicode(value)
        # Important: do NOT include the expected sig in the exception
        # message, since it might leak up to an attacker!
        # TODO: Can we enforce this in the Django debug templates?
        raise BadSignature('Signature "%s" does not match' % sig)


class TimestampSigner(Signer):
    def timestamp(self):
        return baseconv.base62.from_int(int(time.time()))

    def sign(self, value, salt=''):
        value = smart_str('%s%s%s' % (value, self.sep, self.timestamp()))
        return '%s%s%s' % (value, self.sep, self.signature(value, salt=salt))

    def unsign(self, value, salt='', max_age=None):
        value, timestamp = super(TimestampSigner, self).unsign(
            value, salt=salt).rsplit(self.sep, 1)
        timestamp = baseconv.base62.to_int(timestamp)
        if max_age is not None:
            # Check timestamp is not older than max_age
            age = time.time() - timestamp
            if age > max_age:
                raise SignatureExpired(
                    'Signature age %s > %s seconds' % (age, max_age))
        return value
