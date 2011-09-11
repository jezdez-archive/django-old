
from django.utils import unittest
from django.utils.passhash import *


class TestUtilsHashPass(unittest.TestCase):

    def test_simple(self):
        encoded = make_password('letmein')
        self.assertTrue(encoded.startswith('pbkdf2$'))
        self.assertTrue(check_password(u'letmein', encoded))
        self.assertFalse(check_password('letmeinz', encoded))

    def test_pkbdf2(self):
        encoded = make_password('letmein', 'seasalt', 'pbkdf2')
        self.assertEqual(encoded, 'pbkdf2$2000$seasalt$BmIZnhZ3zVdDpviQIvlBPZUHRP/UnT5uEqiSr17zLg4=')
        self.assertTrue(check_password(u'letmein', encoded))
        self.assertFalse(check_password('letmeinz', encoded))

    def test_sha1(self):
        encoded = make_password('letmein', 'seasalt', 'sha1')
        self.assertEqual(encoded, 'sha1$seasalt$fec3530984afba6bade3347b7140d1a7da7da8c7')
        self.assertTrue(check_password(u'letmein', encoded))
        self.assertFalse(check_password('letmeinz', encoded))

    def test_md5(self):
        encoded = make_password('letmein', 'seasalt', 'md5')
        self.assertEqual(encoded, '0d107d09f5bbe40cade3de5c71e9e9b7')
        self.assertTrue(check_password(u'letmein', encoded))
        self.assertFalse(check_password('letmeinz', encoded))

    def test_crypt(self):
        try:
            import crypt
        except ImportError:
            return
        encoded = make_password('letmein', 'ab', 'crypt')
        self.assertEqual(encoded, 'crypt$$abN/qM.L/H8EQ')
        self.assertTrue(check_password(u'letmein', encoded))
        self.assertFalse(check_password('letmeinz', encoded))

    def test_bcrypt(self):
        try:
            import bcrypt
        except ImportError:
            return
        encoded = make_password('letmein', hasher='bcrypt')
        self.assertTrue(encoded.startswith('bcrypt$'))
        self.assertTrue(check_password(u'letmein', encoded))
        self.assertFalse(check_password('letmeinz', encoded))

    def test_unusable(self):
        encoded = make_password(None)
        self.assertFalse(is_password_usable(encoded))
        self.assertFalse(check_password(None, encoded))
        self.assertFalse(check_password(UNUSABLE_PASSWORD, encoded))
        self.assertFalse(check_password('', encoded))
        self.assertFalse(check_password(u'letmein', encoded))
        self.assertFalse(check_password('letmeinz', encoded))

    def test_bad_algorithm(self):
        def doit():
            make_password('letmein', hasher='lolcat')
        self.assertRaises(ValueError, doit)

    def test_low_level_pkbdf2(self):
        hasher = PBKDF2PasswordHasher()
        encoded = hasher.encode('letmein', 'seasalt')
        self.assertEqual(encoded, 'pbkdf2$2000$seasalt$BmIZnhZ3zVdDpviQIvlBPZUHRP/UnT5uEqiSr17zLg4=')
        self.assertTrue(hasher.verify('letmein', encoded))

    def test_upgrade(self):
        self.assertEqual('pbkdf2', get_hasher('default').algorithm)
        for algo in ('sha1', 'md5'):
            encoded = make_password('letmein', hasher=algo)
            state = {'upgraded': False}
            def setter():
                state['upgraded'] = True
            self.assertTrue(check_password('letmein', encoded, setter))
            self.assertTrue(state['upgraded'])

    def test_no_upgrade(self):
        encoded = make_password('letmein')
        state = {'upgraded': False}
        def setter():
            state['upgraded'] = True
        self.assertFalse(check_password('WRONG', encoded, setter))
        self.assertFalse(state['upgraded'])

    def test_no_upgrade_on_incorrect_pass(self):
        self.assertEqual('pbkdf2', get_hasher('default').algorithm)
        for algo in ('sha1', 'md5'):
            encoded = make_password('letmein', hasher=algo)
            state = {'upgraded': False}
            def setter():
                state['upgraded'] = True
            self.assertFalse(check_password('WRONG', encoded, setter))
            self.assertFalse(state['upgraded'])
