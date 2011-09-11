"""
Django's standard crypto functions and utilities.
"""

import hmac
import struct
import hashlib
from django.conf import settings


def salted_hmac(key_salt, value, secret=None):
    """
    Returns the HMAC-SHA1 of 'value', using a key generated from key_salt and a
    secret (which defaults to settings.SECRET_KEY).

    A different key_salt should be passed in for every application of HMAC.
    """
    if secret is None:
        secret = settings.SECRET_KEY

    # We need to generate a derived key from our base key.  We can do this by
    # passing the key_salt and our base key through a pseudo-random function and
    # SHA1 works nicely.
    key = hashlib.sha1(key_salt + secret).digest()

    # If len(key_salt + secret) > sha_constructor().block_size, the above
    # line is redundant and could be replaced by key = key_salt + secret, since
    # the hmac module does the same thing for keys longer than the block size.
    # However, we need to ensure that we *always* do this.
    return hmac.new(key, msg=value, digestmod=hashlib.sha1)


def constant_time_compare(val1, val2):
    """
    Returns True if the two strings are equal, False otherwise.

    The time taken is independent of the number of characters that match.
    """
    if len(val1) != len(val2):
        return False
    result = 0
    for x, y in zip(val1, val2):
        result |= ord(x) ^ ord(y)
    return result == 0


class PBKDF2RandomSource(object):
    """
    Underlying pseudorandom function (PRF) for pbkdf2()

    For example::

        import hashlib
        prf = PBKDF2RandomSource(hashlib.sha256)

    """

    def __init__(self, digest):
        self.digest = digest
        self.digest_size = digest().digest_size

    def __call__(self, key, data):
        return hmac.new(key, data, self.digest).digest()


def pbkdf2(password, salt, iterations=2000, dklen=0, prf=None):
    """
    Implements PBKDF2 as defined in RFC 2898, section 5.2

    Based on a routine written by aaz:
    http://stackoverflow.com/questions/5130513/pbkdf2-hmac-sha2-test-vectors

    DO NOT change the default behavior of this function.  Ever.

    For example::

        >>> pbkdf2("password", "salt", dklen=20).encode('hex')
        'afe6c5530785b6cc6b1c6453384731bd5ee432ee'

    """
    assert iterations > 0
    if not prf:
        prf = PBKDF2RandomSource(hashlib.sha256)
    hlen = prf.digest_size
    if not dklen:
        dklen = hlen
    if dklen > (2 ** 32 - 1) * hlen:
        raise ValueError('dklen too big')
    l = -(-dklen // hlen)
    r = dklen - (l - 1) * hlen

    def int_to_32bit_be(i):
        assert i > 0
        return struct.pack('>I', i)

    def xor_string(A, B):
        return ''.join([chr(ord(a) ^ ord(b)) for a, b in zip(A, B)])

    def F(i):
        def U():
            U = salt + int_to_32bit_be(i)
            for j in range(iterations):
                U = prf(password, U)
                yield U
        return reduce(xor_string, U())

    T = [F(x) for x in range(1, l + 1)]
    dk = ''.join(T[:-1]) + T[-1][:r]
    return dk
