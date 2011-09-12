"""

    django.utils.passhash
    ~~~~~~~~~~~~~~~~~~~~~

    Secure password hashing utilities.

    I implement a variety of hashing algorithms you can use for
    *securely* storing passwords in a database.  The purpose of this
    code is to ensure no one can ever turn a password hash stored in
    your database back into the original password.

"""

import hashlib

from django.conf import settings
from django.utils import importlib
from django.utils.encoding import smart_str
from django.core.exceptions import ImproperlyConfigured
from django.utils.crypto import (
    pbkdf2, constant_time_compare, get_random_string)


UNUSABLE_PASSWORD = '!'  # This will never be a valid encoded hash
HASHERS = None  # lazily loaded from PASSWORD_HASHERS
PREFERRED_HASHER = None  # defaults to first item in PASSWORD_HASHERS


def is_password_usable(encoded):
    return (encoded is not None and encoded != UNUSABLE_PASSWORD)


def check_password(password, encoded, setter=None, preferred='default'):
    """
    Returns a boolean of whether the raw password matches the three
    part encoded digest.

    If setter is specified, it'll be called when you need to
    regenerate the password.
    """
    if not password:
        return False
    if not is_password_usable(encoded):
        return False
    preferred = get_hasher(preferred)
    password = smart_str(password)
    encoded = smart_str(encoded)
    if len(encoded) == 32 and '$' not in encoded:
        hasher = get_hasher('md5')
    else:
        algorithm = encoded.split('$', 1)[0]
        hasher = get_hasher(algorithm)
    must_update = (hasher.algorithm != preferred.algorithm)
    is_correct = hasher.verify(password, encoded)
    if setter and is_correct and must_update:
        setter()
    return is_correct


def make_password(password, salt=None, hasher='default'):
    """
    Turn a plain-text password into a hash for database storage

    Same as encode() but generates a new random salt.  If
    password is None or blank then UNUSABLE_PASSWORD will be
    returned which disallows logins.
    """
    if not password:
        return UNUSABLE_PASSWORD
    hasher = get_hasher(hasher)
    if not salt:
        salt = hasher.gensalt()
    password = smart_str(password)
    salt = smart_str(salt)
    return hasher.encode(password, salt)


def get_hasher(algorithm='default'):
    """
    Returns an instance of a loaded password hasher.

    If algorithm is 'default', the default hasher will be returned.
    This function will also lazy import hashers specified in your
    settings file if needed.
    """
    if hasattr(algorithm, 'algorithm'):
        return algorithm
    elif algorithm == 'default':
        if PREFERRED_HASHER is None:
            load_hashers()
        return PREFERRED_HASHER
    else:
        if HASHERS is None:
            load_hashers()
        if algorithm not in HASHERS:
            raise ValueError(
                ('Unknown password hashing algorithm "%s".  Did you specify '
                 'it in PASSWORD_HASHERS?') % (algorithm))
        return HASHERS[algorithm]


def load_hashers():
    global HASHERS
    global PREFERRED_HASHER
    hashers = []
    for backend in settings.PASSWORD_HASHERS:
        try:
            mod_path, cls_name = backend.rsplit('.', 1)
            mod = importlib.import_module(mod_path)
            hasher_cls = getattr(mod, cls_name)
        except (AttributeError, ImportError, ValueError):
            raise InvalidPasswordHasherError(
                "hasher not found: %s" % (backend))
        hasher = hasher_cls()
        if not getattr(hasher, 'algorithm'):
            raise InvalidPasswordHasherError(
                "hasher doesn't specify an algorithm name: %s" % (backend))
        hashers.append(hasher)
    HASHERS = dict([(hasher.algorithm, hasher) for hasher in hashers])
    PREFERRED_HASHER = hashers[0]


class InvalidPasswordHasherError(ImproperlyConfigured):
    pass


class BasePasswordHasher(object):
    """
    Abstract base class for password hashers

    When creating your own hasher, you need to override algorithm,
    verify() and encode().

    PasswordHasher objects are immutable.
    """
    algorithm = None

    def gensalt(self):
        """
        I should generate cryptographically secure nonce salt in ascii
        """
        return get_random_string()

    def verify(self, password, encoded):
        """
        Abstract method to check if password is correct
        """
        raise NotImplementedError()

    def encode(self, password, salt):
        """
        Abstract method for creating encoded database values

        The result is normally formatted as "algorithm$salt$hash" and
        must be fewer than 128 characters.
        """
        raise NotImplementedError()


class PBKDF2PasswordHasher(BasePasswordHasher):
    """
    Secure password hashing using the PBKDF2 algorithm (recommended)

    I'm configured to use PBKDF2 + HMAC + SHA256 with 10000
    iterations.  The result is a 64 byte binary string.  Iterations
    may be changed safely but you must rename the algorithm if you
    change SHA256.
    """
    algorithm = "pbkdf2"
    iterations = 10000

    def encode(self, password, salt, iterations=None):
        assert password
        assert salt and '$' not in salt
        if not iterations:
            iterations = self.iterations
        hash = pbkdf2(password, salt, iterations)
        hash = hash.encode('base64').strip()
        return "%s$%d$%s$%s" % (self.algorithm, iterations, salt, hash)

    def verify(self, password, encoded):
        algorithm, iterations, salt, hash = encoded.split('$', 3)
        assert algorithm == self.algorithm
        encoded_2 = self.encode(password, salt, int(iterations))
        return constant_time_compare(encoded, encoded_2)


class BCryptPasswordHasher(BasePasswordHasher):
    """
    Secure password hashing using the bcrypt algorithm (recommended)

    This is considered by many to be the most secure algorithm but you
    must first install the py-crypt library.  Please be warned that
    this library depends on native C code and might cause portability
    issues.
    """
    algorithm = "bcrypt"
    rounds = 12

    def _import(self):
        try:
            import bcrypt
        except ImportError:
            raise ValueError('py-bcrypt library not installed')
        return bcrypt

    def gensalt(self):
        bcrypt = self._import()
        return bcrypt.gensalt(self.rounds)

    def encode(self, password, salt):
        bcrypt = self._import()
        data = bcrypt.hashpw(password, salt)
        return "%s$%s" % (self.algorithm, data)

    def verify(self, password, encoded):
        bcrypt = self._import()
        algorithm, data = encoded.split('$', 1)
        assert algorithm == self.algorithm
        return constant_time_compare(data, bcrypt.hashpw(password, data))


class SHA1PasswordHasher(BasePasswordHasher):
    """
    The SHA1 password hashing algorithm (not recommended)
    """
    algorithm = "sha1"

    def encode(self, password, salt):
        assert password
        assert salt and '$' not in salt
        hash = hashlib.sha1(salt + password).hexdigest()
        return "%s$%s$%s" % (self.algorithm, salt, hash)

    def verify(self, password, encoded):
        algorithm, salt, hash = encoded.split('$', 2)
        assert algorithm == self.algorithm
        encoded_2 = self.encode(password, salt)
        return constant_time_compare(encoded, encoded_2)


class MD5PasswordHasher(BasePasswordHasher):
    """
    I am an incredibly insecure algorithm you should *never* use

    I store unsalted MD5 hashes without the algorithm prefix.

    This class is implemented because Django used to store passwords
    this way.  Some older Django installs still have these values
    lingering around so we need to handle and upgrade them properly.
    """
    algorithm = "md5"

    def gensalt(self):
        return ''

    def encode(self, password, salt):
        return hashlib.md5(password).hexdigest()

    def verify(self, password, encoded):
        encoded_2 = self.encode(password, '')
        return constant_time_compare(encoded, encoded_2)


class CryptPasswordHasher(BasePasswordHasher):
    """
    Password hashing using UNIX crypt (not recommended)

    The crypt module is not supported on all platforms.
    """
    algorithm = "crypt"

    def _import(self):
        try:
            import crypt
        except ImportError:
            raise ValueError('"crypt" password algorithm not supported in '
                             'this environment')
        return crypt

    def gensalt(self):
        return get_random_string(2)

    def encode(self, password, salt):
        crypt = self._import()
        assert len(salt) == 2
        data = crypt.crypt(password, salt)
        # we don't need to store the salt, but django used to do this
        return "%s$%s$%s" % (self.algorithm, '', data)

    def verify(self, password, encoded):
        crypt = self._import()
        algorithm, salt, data = encoded.split('$', 2)
        assert algorithm == self.algorithm
        return constant_time_compare(data, crypt.crypt(password, data))
