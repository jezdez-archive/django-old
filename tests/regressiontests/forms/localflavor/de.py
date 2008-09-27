# -*- coding: utf-8 -*-
# Tests for the contrib/localflavor/ DE form fields.

tests = r"""
# DEZipCodeField ##############################################################

>>> from django.contrib.localflavor.de.forms import DEZipCodeField
>>> f = DEZipCodeField()
>>> f.clean('99423')
u'99423'
>>> f.clean(' 99423')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX.']

# DEPhoneDIN5008Field #############################################################

>>> from django.contrib.localflavor.de.forms import DEPhoneNumberField
>>> f = DEPhoneNumberField()
>>> f.clean('030 12345-67') # new DIN 5008
u'030 12345-67'
>>> f.clean('030 1234567') # new DIN 5008
u'030 1234567'
>>> f.clean('0301234567') # lazy DIN 5008
u'0301234567'
>>> f.clean('(0 30) 1 23 45-67') # old DIN 5008
u'(0 30) 1 23 45-67'
>>> f.clean('(0 30) 1 23 456') # old DIN 5008
u'(0 30) 1 23 456'
>>> f.clean('0900 5 123456') # DIN 5008 Premium rate numbers
u'0900 5 123456'
>>> f.clean('(030) 123 45 67') # E.123
u'(030) 123 45 67'
>>> f.clean('+49 (30) 1234567') # Microsoft/TAPI
u'+49 (30) 1234567'
>>> f.clean('+49 (0)30 12345-67') # Informal standard in Germany and Austria
u'+49 (0)30 12345-67'
>>> f.clean('+49 30 12345-67') # DIN 5008
u'+49 30 12345-67'
>>> f.clean('+49 30 1234567') # E.123
u'+49 30 1234567'
>>> f.clean('+49 30 12345-67') # E.123
u'+49 30 12345-67'
>>> f.clean('+49301234567') # Lazy E.123
u'+49301234567'
>>> f.clean('+49 30 12345--67')
Traceback (most recent call last):
...
ValidationError: [u'Enter the phone number in a supported format: DIN 5008, E.123, Microsoft/TAPI.']
>>> f.clean('+49 (030) 1234567')
Traceback (most recent call last):
...
ValidationError: [u'Enter the phone number in a supported format: DIN 5008, E.123, Microsoft/TAPI.']
>>> f.clean('(030) (123) 45 67')
Traceback (most recent call last):
...
ValidationError: [u'Enter the phone number in a supported format: DIN 5008, E.123, Microsoft/TAPI.']
>>> f.clean('abcdefg')
Traceback (most recent call last):
ValidationError: [u'Enter the phone number in a supported format: DIN 5008, E.123, Microsoft/TAPI.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f = DEPhoneNumberField(required=False)
>>> f.clean(None)
u''
>>> f.clean('')
u''


# DEStateSelect #############################################################

>>> from django.contrib.localflavor.de.forms import DEStateSelect
>>> w = DEStateSelect()
>>> w.render('states', 'TH')
u'<select name="states">\n<option value="BW">Baden-Wuerttemberg</option>\n<option value="BY">Bavaria</option>\n<option value="BE">Berlin</option>\n<option value="BB">Brandenburg</option>\n<option value="HB">Bremen</option>\n<option value="HH">Hamburg</option>\n<option value="HE">Hessen</option>\n<option value="MV">Mecklenburg-Western Pomerania</option>\n<option value="NI">Lower Saxony</option>\n<option value="NW">North Rhine-Westphalia</option>\n<option value="RP">Rhineland-Palatinate</option>\n<option value="SL">Saarland</option>\n<option value="SN">Saxony</option>\n<option value="ST">Saxony-Anhalt</option>\n<option value="SH">Schleswig-Holstein</option>\n<option value="TH" selected="selected">Thuringia</option>\n</select>'

# DEIdentityCardNumberField #################################################

>>> from django.contrib.localflavor.de.forms import DEIdentityCardNumberField
>>> f = DEIdentityCardNumberField()
>>> f.clean('7549313035D-6004103-0903042-0')
u'7549313035D-6004103-0903042-0'
>>> f.clean('9786324830D 6104243 0910271 2')
u'9786324830D-6104243-0910271-2'
>>> f.clean('0434657485D-6407276-0508137-9')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid German identity card number in XXXXXXXXXXX-XXXXXXX-XXXXXXX-X format.']
"""
