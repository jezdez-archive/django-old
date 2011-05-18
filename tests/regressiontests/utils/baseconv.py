from unittest import TestCase
from django.utils.baseconv import base2, base16, base36, base62

class TestBaseConv(TestCase):

    def test_baseconv(self):
        nums = [-10 ** 10, 10 ** 10] + range(-100, 100)
        for convertor in [base2, base16, base36, base62]:
            for i in nums:
                self.assertEqual(i, convertor.decode(convertor.encode(i)))

