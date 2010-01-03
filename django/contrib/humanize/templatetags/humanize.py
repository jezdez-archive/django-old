import re
from datetime import date
from django.utils.translation import ungettext, ugettext as _
from django.utils.encoding import force_unicode
from django.utils.formats import number_format
from django import template
from django.template import defaultfilters
from django.conf import settings

register = template.Library()

def ordinal(value):
    """
    Converts an integer to its ordinal as a string. 1 is '1st', 2 is '2nd',
    3 is '3rd', etc. Works for any integer.
    """
    try:
        value = int(value)
    except (TypeError, ValueError):
        return value
    t = (_('th'), _('st'), _('nd'), _('rd'), _('th'), _('th'), _('th'), _('th'), _('th'), _('th'))
    if value % 100 in (11, 12, 13): # special case
        return u"%d%s" % (value, t[0])
    return u'%d%s' % (value, t[value % 10])
ordinal.is_safe = True
register.filter(ordinal)

def intcomma(value):
    """
    Converts an integer to a string containing commas every three digits.
    For example, 3000 becomes '3,000' and 45000 becomes '45,000'.
    """
    if settings.USE_L10N:
        return number_format(value)
    orig = force_unicode(value)
    new = re.sub("^(-?\d+)(\d{3})", '\g<1>,\g<2>', orig)
    if orig == new:
        return new
    else:
        return intcomma(new)
intcomma.is_safe = True
register.filter(intcomma)

def intword(value):
    """
    Converts a large integer to a friendly text representation. Works best for
    numbers over 1 million. For example, 1000000 becomes '1.0 million', 1200000
    becomes '1.2 million' and '1200000000' becomes '1.2 billion'.
    """
    value = int(value)
    if value < 1000000:
        return value

    def _check_for_i18n(value, float_formatted, string_formatted):
        """
        Use the i18n enabled defaultfilters.floatformat if possible
        """
        if settings.USE_L10N:
            return defaultfilters.floatformat(value, 1), string_formatted
        return value, float_formatted

    if value < 1000000000:
        new_value = value / 1000000.0
        new_value, value_string = _check_for_i18n(new_value,
            ungettext('%(value).1f million', '%(value).1f million', new_value),
            ungettext('%(value)s million', '%(value)s million', new_value))
        return value_string % {'value': new_value}
    if value < 1000000000000:
        new_value = value / 1000000000.0
        new_value, value_string = _check_for_i18n(new_value,
            ungettext('%(value).1f billion', '%(value).1f billion', new_value),
            ungettext('%(value)s billion', '%(value)s billion', new_value))
        return value_string % {'value': new_value}
    if value < 1000000000000000:
        new_value = value / 1000000000000.0
        new_value, value_string = _check_for_i18n(new_value,
            ungettext('%(value).1f trillion', '%(value).1f trillion', new_value),
            ungettext('%(value)s trillion', '%(value)s trillion', new_value))
        return value_string % {'value': new_value}
    return value
intword.is_safe = False
register.filter(intword)

def apnumber(value):
    """
    For numbers 1-9, returns the number spelled out. Otherwise, returns the
    number. This follows Associated Press style.
    """
    try:
        value = int(value)
    except ValueError:
        return value
    if not 0 < value < 10:
        return value
    return (_('one'), _('two'), _('three'), _('four'), _('five'), _('six'), _('seven'), _('eight'), _('nine'))[value-1]
apnumber.is_safe = True
register.filter(apnumber)

def naturalday(value, arg=None):
    """
    For date values that are tomorrow, today or yesterday compared to
    present day returns representing string. Otherwise, returns a string
    formatted according to settings.DATE_FORMAT.
    """
    try: 
        value = date(value.year, value.month, value.day)
    except AttributeError:
        # Passed value wasn't a date object
        return value
    except ValueError:
        # Date arguments out of range
        return value
    delta = value - date.today()
    if delta.days == 0:
        return _(u'today')
    elif delta.days == 1:
        return _(u'tomorrow')
    elif delta.days == -1:
        return _(u'yesterday')
    return defaultfilters.date(value, arg)
register.filter(naturalday)
