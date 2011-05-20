from unittest import TestCase
from django.utils.baseconv import base2, base16, base36, base56, base62, base64, BaseConverter

class TestBaseConv(TestCase):

    def test_baseconv(self):
        nums = [-10 ** 10, 10 ** 10] + range(-100, 100)
        for converter in [base2, base16, base36, base56, base62, base64]:
            if converter.sign == '-':
                for i in nums:
                    self.assertEqual(i, converter.decode(converter.encode(i)))
            else:
                for i in nums:
                    i = str(i)
                    if i[0] == '-':
                        i = converter.sign + i[1:]
                    self.assertEqual(i, converter.decode(converter.encode(i)))

    def test_base20(self):
        base20 = BaseConverter('0123456789abcdefghij')
        self.assertEqual(base20.encode(1234), '31e')
        self.assertEqual(base20.decode('31e'), 1234)
        self.assertEqual(base20.encode(-1234), '-31e')
        self.assertEqual(base20.decode('-31e'), -1234)

    def test_base11(self):
        base11 = BaseConverter('0123456789-', sign='$')
        self.assertEqual(base11.encode('$1234'), '$-22')
        self.assertEqual(base11.decode('$-22'), '$1234')
