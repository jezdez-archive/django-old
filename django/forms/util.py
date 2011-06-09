from django.utils.html import conditional_escape
from django.utils.encoding import StrAndUnicode, force_unicode
from django.template.loader import render_to_string

# Import ValidationError so that it can be imported from this
# module to maintain backwards compatibility.
from django.core.exceptions import ValidationError

def flatatt(attrs):
    """
    Convert a dictionary of attributes to a single string.
    The returned string will contain a leading space followed by key="value",
    XML-style pairs.  It is assumed that the keys do not need to be XML-escaped.
    If the passed dictionary is empty, then return an empty string.
    """
    return u''.join([u' %s="%s"' % (k, conditional_escape(v)) for k, v in attrs.items()])

class ErrorDict(dict, StrAndUnicode):
    """
    A collection of errors that knows how to display itself in various formats.

    The dictionary keys are the field names, and the values are the errors.
    """
    def __unicode__(self):
        return self.as_ul()

    def as_ul(self):
        if not self: return u''
        return render_to_string('forms/layouts/default/errordict.html', {
            'errordict': self,
        })

    def as_text(self):
        return u'\n'.join([u'* %s\n%s' % (k, u'\n'.join([u'  * %s' % force_unicode(i) for i in v])) for k, v in self.items()])

class ErrorList(list, StrAndUnicode):
    """
    A collection of errors that knows how to display itself in various formats.
    """
    def __unicode__(self):
        return self.as_ul()

    def as_ul(self):
        if not self: return u''
        return render_to_string('forms/layouts/default/errorlist.html', {
            'errorlist': self,
        })

    def as_text(self):
        if not self: return u''
        return u'\n'.join([u'* %s' % force_unicode(e) for e in self])

    def __repr__(self):
        return repr([force_unicode(e) for e in self])

