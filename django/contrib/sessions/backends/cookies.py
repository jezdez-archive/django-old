import zlib
try:
    import cPickle as pickle
except ImportError:
    import pickle

from django.conf import settings
from django.core import signing
from django.utils.encoding import smart_str

from django.contrib.sessions.backends.base import SessionBase


class SessionStore(SessionBase):
    salt = 'django.contrib.sessions.backends.cookies'

    def load(self):
        """
        We load the data from the key itself instead of fetching from some
        external data store. Opposite of _get_session_key(), raises
        BadSignature if signature fails.
        """
        signer = signing.TimestampSigner(salt=self.salt)
        try:
            base64d = signer.unsign(
                self._session_key, max_age=settings.SESSION_COOKIE_AGE)
            pickled = signing.b64_decode(smart_str(base64d))
            return pickle.loads(zlib.decompress(pickled))
        except (signing.BadSignature, ValueError):
            self.create()
            return {}

    def create(self):
        """
        To create a new key, we simply make sure that the modified flag is set
        so that the cookie is set on the client for the current request.
        """
        self.modified = True

    def save(self):
        """
        To save, we get the session key as a securely signed string and then
        set the modified flag so that the cookie is set on the client for the
        current request.
        """
        self._session_key = self._get_session_key()
        self.modified = True

    def exists(self, session_key=None):
        """
        This method makes sense when you're talking to a shared resource, but
        it doesn't matter when you're storing the information in the client's
        cookie.
        """
        return False

    def delete(self, session_key=None):
        """
        To delete, we clear the session key and the underlying data structure
        and set the modified flag so that the cookie is set on the client for
        the current request.
        """
        self._session_key = ''
        self._session_cache = {}
        self.modified = True

    def cycle_key(self):
        """
        Keeps the same data but with a new key.  To do this, we just have to
        call ``save()`` and it will automatically save a cookie with a new key
        at the end of the request.
        """
        self.save()

    def _get_session_key(self):
        """
        Most session backends don't need to override this method, but we do,
        because instead of generating a random string, we want to actually
        generate a secure url-safe Base64-encoded string of data as our
        session key.
        """
        payload = getattr(self, '_session_cache', {})
        pickled = pickle.dumps(payload, pickle.HIGHEST_PROTOCOL)
        base64d = signing.b64_encode(zlib.compress(pickled))
        return signing.TimestampSigner(salt=self.salt).sign(base64d)

    def _set_session_key(self, session_key):
        self._session_key = session_key

    session_key = property(_get_session_key, _set_session_key)
