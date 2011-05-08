from django.test import TestCase
from django.http import HttpRequest, HttpResponse
from django.core import signing
import time

class SignedCookieTest(TestCase):

    def test_can_set_and_read_signed_cookies(self):
        response = HttpResponse()
        response.set_signed_cookie('c', 'hello')
        self.assert_('c' in response.cookies)
        self.assert_(response.cookies['c'].value.startswith('hello:'))
        request = HttpRequest()
        request.COOKIES['c'] = response.cookies['c'].value
        value = request.get_signed_cookie('c')
        self.assertEqual(value, u'hello')

    def test_can_use_salt(self):
        response = HttpResponse()
        response.set_signed_cookie('a', 'hello', salt='one')
        request = HttpRequest()
        request.COOKIES['a'] = response.cookies['a'].value
        value = request.get_signed_cookie('a', salt='one')
        self.assertEqual(value, u'hello')
        self.assertRaises(signing.BadSignature,
            request.get_signed_cookie, 'a', salt='two'
        )

    def test_detects_tampering(self):
        response = HttpResponse()
        response.set_signed_cookie('c', 'hello')
        request = HttpRequest()
        request.COOKIES['c'] = response.cookies['c'].value[:-2] + '$$'
        self.assertRaises(signing.BadSignature,
            request.get_signed_cookie, 'c'
        )

    def test_default_argument_supresses_exceptions(self):
        response = HttpResponse()
        response.set_signed_cookie('c', 'hello')
        request = HttpRequest()
        request.COOKIES['c'] = response.cookies['c'].value[:-2] + '$$'
        self.assertEqual(request.get_signed_cookie('c', default=None), None)

    def test_max_age_argument(self):
        old_time = time.time
        time.time = lambda: 123456789
        v = u'hello'
        try:
            response = HttpResponse()
            response.set_signed_cookie('c', v)
            request = HttpRequest()
            request.COOKIES['c'] = response.cookies['c'].value

            self.assertEqual(request.get_signed_cookie('c'), v)

            time.time = lambda: 123456800

            self.assertEqual(request.get_signed_cookie('c', max_age=12), v)
            self.assertEqual(request.get_signed_cookie('c', max_age=11), v)
            self.assertRaises(
                signing.SignatureExpired, request.get_signed_cookie, 'c',
                max_age = 10
            )
        finally:
            time.time = old_time

