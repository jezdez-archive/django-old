"""
HTML Widget classes
"""

import copy
import datetime
from itertools import chain
from urlparse import urljoin
from util import flatatt

from django.conf import settings
from django.template import loader, Context
from django.utils import datetime_safe, formats
from django.utils.datastructures import MultiValueDict, MergeDict
from django.utils.encoding import StrAndUnicode, force_unicode
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext, ugettext_lazy

__all__ = (
    'Media', 'MediaDefiningClass', 'Widget', 'TextInput', 'PasswordInput',
    'HiddenInput', 'MultipleHiddenInput', 'ClearableFileInput',
    'FileInput', 'DateInput', 'DateTimeInput', 'TimeInput', 'Textarea',
    'CheckboxInput', 'Select', 'NullBooleanSelect', 'SelectMultiple',
    'RadioSelect', 'CheckboxSelectMultiple', 'MultiWidget',
    'SplitDateTimeWidget',
)

MEDIA_TYPES = ('css', 'js')


class Media(StrAndUnicode):
    def __init__(self, media=None, **kwargs):
        if media:
            media_attrs = media.__dict__
        else:
            media_attrs = kwargs

        self._css = {}
        self._js = []

        for name in MEDIA_TYPES:
            getattr(self, 'add_' + name)(media_attrs.get(name, None))

        # Any leftover attributes must be invalid.
        # if media_attrs != {}:
        #     raise TypeError("'class Media' has invalid attribute(s): %s" % ','.join(media_attrs.keys()))

    def __unicode__(self):
        return self.render()

    def render(self):
        return mark_safe(u'\n'.join(chain(*[getattr(self, 'render_' + name)() for name in MEDIA_TYPES])))

    def render_js(self):
        return [u'<script type="text/javascript" src="%s"></script>' % self.absolute_path(path) for path in self._js]

    def render_css(self):
        # To keep rendering order consistent, we can't just iterate over items().
        # We need to sort the keys, and iterate over the sorted list.
        media = self._css.keys()
        media.sort()
        return chain(*[
            [u'<link href="%s" type="text/css" media="%s" rel="stylesheet" />' % (self.absolute_path(path), medium)
                    for path in self._css[medium]]
                for medium in media])

    def absolute_path(self, path, prefix=None):
        if path.startswith(u'http://') or path.startswith(u'https://') or path.startswith(u'/'):
            return path
        if prefix is None:
            if settings.STATIC_URL is None:
                 # backwards compatibility
                prefix = settings.MEDIA_URL
            else:
                prefix = settings.STATIC_URL
        return urljoin(prefix, path)

    def __getitem__(self, name):
        "Returns a Media object that only contains media of the given type"
        if name in MEDIA_TYPES:
            return Media(**{str(name): getattr(self, '_' + name)})
        raise KeyError('Unknown media type "%s"' % name)

    def add_js(self, data):
        if data:
            for path in data:
                if path not in self._js:
                    self._js.append(path)

    def add_css(self, data):
        if data:
            for medium, paths in data.items():
                for path in paths:
                    if not self._css.get(medium) or path not in self._css[medium]:
                        self._css.setdefault(medium, []).append(path)

    def __add__(self, other):
        combined = Media()
        for name in MEDIA_TYPES:
            getattr(combined, 'add_' + name)(getattr(self, '_' + name, None))
            getattr(combined, 'add_' + name)(getattr(other, '_' + name, None))
        return combined


def media_property(cls):
    def _media(self):
        # Get the media property of the superclass, if it exists
        if hasattr(super(cls, self), 'media'):
            base = super(cls, self).media
        else:
            base = Media()

        # Get the media definition for this class
        definition = getattr(cls, 'Media', None)
        if definition:
            extend = getattr(definition, 'extend', True)
            if extend:
                if extend == True:
                    m = base
                else:
                    m = Media()
                    for medium in extend:
                        m = m + base[medium]
                return m + Media(definition)
            else:
                return Media(definition)
        else:
            return base
    return property(_media)


class MediaDefiningClass(type):
    "Metaclass for classes that can have media definitions"
    def __new__(cls, name, bases, attrs):
        new_class = super(MediaDefiningClass, cls).__new__(cls, name, bases,
                                                           attrs)
        if 'media' not in attrs:
            new_class.media = media_property(new_class)
        return new_class


class Widget(object):
    __metaclass__ = MediaDefiningClass
    is_hidden = False  # Determines whether this corresponds to
                       # an <input type="hidden">.
    needs_multipart_form = False  # Determines does this widget need
                                  # multipart-encrypted form
    is_localized = False
    is_required = False
    template_name = None  # The template used to render this form

    def __init__(self, attrs=None, template_name=None):
        if attrs is not None:
            self.attrs = attrs.copy()
        else:
            self.attrs = {}
        if template_name is not None:
            self.template_name = template_name

    def __deepcopy__(self, memo):
        obj = copy.copy(self)
        obj.attrs = self.attrs.copy()
        memo[id(self)] = obj
        return obj

    def render(self, name, value, attrs=None, template_name=None, extra_context=None, context_instance=None):
        """
        Returns this Widget rendered as HTML, as a Unicode string.

        The 'value' given is not guaranteed to be valid input, so subclass
        implementations should program defensively.
        """
        context = self.get_context(name, value, attrs=attrs,
            extra_context=extra_context, context_instance=context_instance)
        if template_name is None:
            template_name = self.template_name
        return loader.render_to_string(template_name, context)

    def get_context(self, name, value, attrs=None, extra_context=None, context_instance=None):
        final_attrs = self.build_attrs(attrs)
        if 'name' in final_attrs:
            final_attrs.pop('name')
        context = {
            'attrs': final_attrs,
            'hidden': self.is_hidden,
            'name': name,
            'required': self.is_required,
        }
        context.update(self.get_context_data())
        if extra_context is not None:
            context.update(extra_context)
        if context_instance is None:
            return Context(context)
        context_instance.update(context)
        return context_instance

    def get_context_data(self):
        return {}

    def build_attrs(self, extra_attrs=None, **kwargs):
        "Helper function for building an attribute dictionary."
        attrs = dict(self.attrs, **kwargs)
        if extra_attrs:
            attrs.update(extra_attrs)
        return attrs

    def value_from_datadict(self, data, files, name):
        """
        Given a dictionary of data and this widget's name, returns the value
        of this widget. Returns None if it's not provided.
        """
        return data.get(name, None)

    def _has_changed(self, initial, data):
        """
        Return True if data differs from initial.
        """
        # For purposes of seeing whether something has changed, None is
        # the same as an empty string, if the data or inital value we get
        # is None, replace it w/ u''.
        if data is None:
            data_value = u''
        else:
            data_value = data
        if initial is None:
            initial_value = u''
        else:
            initial_value = initial
        if force_unicode(initial_value) != force_unicode(data_value):
            return True
        return False

    def id_for_label(self, id_):
        """
        Returns the HTML ID attribute of this Widget for use by a <label>,
        given the ID of the field. Returns None if no ID is available.

        This hook is necessary because some widgets have multiple HTML
        elements and, thus, multiple IDs. In that case, this method should
        return an ID value that corresponds to the first ID in the widget's
        tags.
        """
        return id_
    id_for_label = classmethod(id_for_label)


class Input(Widget):
    """
    Base class for all <input> widgets (except type='checkbox' and
    type='radio', which are special).
    """
    input_type = None  # Subclasses must define this.
    template_name = 'forms/widgets/input.html'

    def get_context(self, name, value, attrs=None, **kwargs):
        context = super(Input, self).get_context(name, value, attrs=attrs, **kwargs)
        context['type'] = self.input_type
        context.update(self.get_context_data())

        if value is None:
            value = ''

        if value != '':
            # Only add the 'value' attribute if a value is non-empty.
            context['value'] = force_unicode(self._format_value(value))
        return context


    def _format_value(self, value):
        if self.is_localized:
            return formats.localize_input(value)
        return value


class TextInput(Input):
    input_type = 'text'


class PasswordInput(Input):
    input_type = 'password'

    def __init__(self, attrs=None, render_value=False, template_name=None):
        super(PasswordInput, self).__init__(attrs=attrs, template_name=template_name)
        self.render_value = render_value

    def render(self, name, value, attrs=None, **kwargs):
        if not self.render_value:
            value=None
        return super(PasswordInput, self).render(name, value, attrs=attrs, **kwargs)


class HiddenInput(Input):
    input_type = 'hidden'
    is_hidden = True


class MultipleHiddenInput(HiddenInput):
    """
    A widget that handles <input type="hidden"> for fields that have a list
    of values.
    """
    def __init__(self, attrs=None, choices=(), template_name=None):
        super(MultipleHiddenInput, self).__init__(
            attrs=attrs, template_name=template_name)
        # choices can be any iterable
        self.choices = choices

    def render(self, name, value, attrs=None, choices=(), template_name=None, **kwargs):
        if value is None: value = []
        final_attrs = self.build_attrs(attrs)
        id_ = final_attrs.get('id', None)
        inputs = []
        if template_name is None:
            template_name = self.template_name
        for i, v in enumerate(value):
            input_attrs = final_attrs
            if id_:
                # An ID attribute was given. Add a numeric index as a suffix
                # so that the inputs don't all have the same ID attribute.
                input_attrs['id'] = '%s_%s' % (id_, i)
            input_ = HiddenInput()
            input_.is_required = self.is_required
            inputs.append(input_.render(
                name, force_unicode(v), attrs=input_attrs,
                template_name=template_name, **kwargs))
        return u''.join(inputs)

    def value_from_datadict(self, data, files, name):
        if isinstance(data, (MultiValueDict, MergeDict)):
            return data.getlist(name)
        return data.get(name, None)


class BaseFileInput(Input):
    input_type = 'file'
    needs_multipart_form = True

    def value_from_datadict(self, data, files, name):
        "File widgets take data from FILES, not POST"
        return files.get(name, None)

    def _has_changed(self, initial, data):
        if data is None:
            return False
        return True


class FileInput(BaseFileInput):
    def render(self, name, value, attrs=None, **kwargs):
        return super(FileInput, self).render(name, None, attrs=attrs, **kwargs)

FILE_INPUT_CONTRADICTION = object()


class ClearableFileInput(BaseFileInput):
    template_name = 'forms/widgets/clearable_input.html'
    initial_text = ugettext_lazy('Currently')
    input_text = ugettext_lazy('Change')
    clear_checkbox_label = ugettext_lazy('Clear')

    def clear_checkbox_name(self, name):
        """
        Given the name of the file input, return the name of the clear checkbox
        input.
        """
        return name + '-clear'

    def clear_checkbox_id(self, name):
        """
        Given the name of the clear checkbox input, return the HTML id for it.
        """
        return name + '_id'

    def get_context(self, name, value, attrs=None, **kwargs):
        context = super(ClearableFileInput, self).get_context(name, value, attrs=attrs, **kwargs)
        checkbox_name = self.clear_checkbox_name(name)
        checkbox_id = self.clear_checkbox_id(checkbox_name)
        context.update({
            'initial_text': self.initial_text,
            'input_text': self.input_text,
            'checkbox_name': checkbox_name,
            'checkbox_id': checkbox_id,
            'clear_checkbox_label': self.clear_checkbox_label,
            'value': value,
        })
        return context

    def value_from_datadict(self, data, files, name):
        upload = super(ClearableFileInput,
                       self).value_from_datadict(data, files, name)
        if not self.is_required and CheckboxInput().value_from_datadict(
            data, files, self.clear_checkbox_name(name)):
            if upload:
                # If the user contradicts themselves (uploads a new file AND
                # checks the "clear" checkbox), we return a unique marker
                # object that FileField will turn into a ValidationError.
                return FILE_INPUT_CONTRADICTION
            # False signals to clear any existing value, as opposed to just None
            return False
        return upload


class Textarea(Widget):
    template_name = 'forms/widgets/textarea.html'

    def __init__(self, attrs=None, template_name=None):
        # The 'rows' and 'cols' attributes are required for HTML correctness.
        default_attrs = {'cols': '40', 'rows': '10'}
        if attrs:
            default_attrs.update(attrs)
        super(Textarea, self).__init__(
            attrs=default_attrs, template_name=template_name)

    def get_context(self, name, value, attrs=None, extra_context=None, context_instance=None):
        if value is None:
            value = ''
        context = {
            'attrs': self.build_attrs(attrs),
            'name': name,
            'value': value,
        }
        context.update(self.get_context_data())
        if extra_context is not None:
            context.update(extra_context)
        return context


class DateInput(Input):
    input_type = 'text'

    def __init__(self, attrs=None, format=None, template_name=None):
        super(DateInput, self).__init__(
            attrs=attrs, template_name=template_name)
        if format:
            self.format = format
            self.manual_format = True
        else:
            self.format = formats.get_format('DATE_INPUT_FORMATS')[0]
            self.manual_format = False

    def _format_value(self, value):
        if self.is_localized and not self.manual_format:
            return formats.localize_input(value)
        elif hasattr(value, 'strftime'):
            value = datetime_safe.new_date(value)
            return value.strftime(self.format)
        return value

    def _has_changed(self, initial, data):
        # If our field has show_hidden_initial=True, initial will be a string
        # formatted by HiddenInput using formats.localize_input, which is not
        # necessarily the format used for this widget. Attempt to convert it.
        try:
            input_format = formats.get_format('DATE_INPUT_FORMATS')[0]
            initial = datetime.datetime.strptime(initial, input_format).date()
        except (TypeError, ValueError):
            pass
        return super(DateInput, self)._has_changed(self._format_value(initial), data)


class DateTimeInput(Input):
    input_type = 'text'

    def __init__(self, attrs=None, format=None, template_name=None):
        super(DateTimeInput, self).__init__(
            attrs=attrs, template_name=template_name)
        if format:
            self.format = format
            self.manual_format = True
        else:
            self.format = formats.get_format('DATETIME_INPUT_FORMATS')[0]
            self.manual_format = False

    def _format_value(self, value):
        if self.is_localized and not self.manual_format:
            return formats.localize_input(value)
        elif hasattr(value, 'strftime'):
            value = datetime_safe.new_datetime(value)
            return value.strftime(self.format)
        return value

    def _has_changed(self, initial, data):
        # If our field has show_hidden_initial=True, initial will be a string
        # formatted by HiddenInput using formats.localize_input, which is not
        # necessarily the format used for this widget. Attempt to convert it.
        try:
            input_format = formats.get_format('DATETIME_INPUT_FORMATS')[0]
            initial = datetime.datetime.strptime(initial, input_format)
        except (TypeError, ValueError):
            pass
        return super(DateTimeInput, self)._has_changed(self._format_value(initial), data)


class TimeInput(Input):
    input_type = 'text'

    def __init__(self, attrs=None, format=None, template_name=None):
        super(TimeInput, self).__init__(
            attrs=attrs, template_name=template_name)
        if format:
            self.format = format
            self.manual_format = True
        else:
            self.format = formats.get_format('TIME_INPUT_FORMATS')[0]
            self.manual_format = False

    def _format_value(self, value):
        if self.is_localized and not self.manual_format:
            return formats.localize_input(value)
        elif hasattr(value, 'strftime'):
            return value.strftime(self.format)
        return value

    def _has_changed(self, initial, data):
        # If our field has show_hidden_initial=True, initial will be a string
        # formatted by HiddenInput using formats.localize_input, which is not
        # necessarily the format used for this  widget. Attempt to convert it.
        try:
            input_format = formats.get_format('TIME_INPUT_FORMATS')[0]
            initial = datetime.datetime.strptime(initial, input_format).time()
        except (TypeError, ValueError):
            pass
        return super(TimeInput, self)._has_changed(self._format_value(initial), data)


class CheckboxInput(Input):
    input_type = 'checkbox'

    def __init__(self, attrs=None, check_test=bool, template_name=None):
        super(CheckboxInput, self).__init__(
            attrs=attrs, template_name=template_name)
        # check_test is a callable that takes a value and returns True
        # if the checkbox should be checked for that value.
        self.check_test = check_test

    def get_context(self, name, value, attrs=None, **kwargs):
        final_attrs = self.build_attrs(attrs)
        try:
            result = self.check_test(value)
        except: # Silently catch exceptions
            result = False
        if result:
            final_attrs['checked'] = 'checked'
        context = super(CheckboxInput, self).get_context(name, None, attrs=final_attrs, **kwargs)
        context.update(self.get_context_data())

        if value not in ('', True, False, None):
            # Only add the 'value' attribute if a value is non-empty.
            context['value'] = force_unicode(value)
        return context

    def value_from_datadict(self, data, files, name):
        if name not in data:
            # A missing value means False because HTML form submission does not
            # send results for unselected checkboxes.
            return False
        value = data.get(name)
        # Translate true and false strings to boolean values.
        values =  {'true': True, 'false': False}
        if isinstance(value, basestring):
            value = values.get(value.lower(), value)
        return value

    def _has_changed(self, initial, data):
        # Sometimes data or initial could be None or u'' which should be the
        # same thing as False.
        return bool(initial) != bool(data)

class Select(Widget):
    template_name = 'forms/widgets/select.html'

    def __init__(self, attrs=None, choices=(), template_name=None):
        super(Select, self).__init__(
            attrs=attrs, template_name=template_name)
        # choices can be any iterable, but we may need to render this widget
        # multiple times. Thus, collapse it into a list so it can be consumed
        # more than once.
        self.choices = list(choices)

    def render(self, name, value, attrs=None, choices=(), template_name=None, extra_context=None, context_instance=None):
        context = self.get_context(name, value, attrs, choices=choices, extra_context=extra_context, context_instance=context_instance)
        if template_name is None:
            template_name = self.template_name
        return loader.render_to_string(template_name, context)

    def get_context(self, name, value, attrs=None, choices=(), extra_context=None, **kwargs):
        if value is None:
            value = ''
        context = super(Select, self).get_context(name, value, attrs=attrs, extra_context=extra_context, **kwargs)

        final_choices = []
        for option_value, option_label in chain(self.choices, choices):
            if isinstance(option_label, (list, tuple)):
                optgroup = {'label': force_unicode(option_value),
                            'choices': option_label}
                final_choices.append(optgroup)
            else:
                final_choices.append((force_unicode(option_value),
                                      option_label))
        context.update({
            'choices': final_choices,
            'value': force_unicode(value),
        })
        if extra_context is not None:
            context.update(extra_context)
        return context


class NullBooleanSelect(Select):
    """
    A Select Widget intended to be used with NullBooleanField.
    """
    def __init__(self, attrs=None, template_name=None):
        choices = ((u'1', ugettext('Unknown')),
                   (u'2', ugettext('Yes')),
                   (u'3', ugettext('No')))
        super(NullBooleanSelect, self).__init__(
            attrs=attrs, template_name=template_name, choices=choices)

    def render(self, name, value, attrs=None, choices=(), **kwargs):
        try:
            value = {True: u'2', False: u'3', u'2': u'2', u'3': u'3'}[value]
        except KeyError:
            value = u'1'
        return super(NullBooleanSelect, self).render(
            name, value, attrs=attrs, choices=choices, **kwargs)

    def value_from_datadict(self, data, files, name):
        value = data.get(name, None)
        return {u'2': True,
                True: True,
                'True': True,
                u'3': False,
                'False': False,
                False: False}.get(value, None)

    def _has_changed(self, initial, data):
        # For a NullBooleanSelect, None (unknown) and False (No)
        # are not the same
        if initial is not None:
            initial = bool(initial)
        if data is not None:
            data = bool(data)
        return initial != data


class SelectMultiple(Select):
    def render(self, name, value, attrs=None, choices=(), **kwargs):
        if value is None:
            value = []
        return super(SelectMultiple, self).render(
            name, value, attrs=attrs, choices=choices, **kwargs)

    def get_context(self, name, value, attrs, choices, extra_context=None, **kwargs):
        context = super(SelectMultiple, self).get_context(
            name, value, attrs=attrs, choices=choices, **kwargs)
        context.update({
            'value': map(force_unicode, value),
            'multiple': True,
        })
        if extra_context is not None:
            context.update(extra_context)
        return context

    def value_from_datadict(self, data, files, name):
        if isinstance(data, (MultiValueDict, MergeDict)):
            return data.getlist(name)
        return data.get(name, None)

    def _has_changed(self, initial, data):
        if initial is None:
            initial = []
        if data is None:
            data = []
        if len(initial) != len(data):
            return True
        initial_set = set([force_unicode(value) for value in initial])
        data_set = set([force_unicode(value) for value in data])
        return data_set != initial_set

class RadioInput(StrAndUnicode):
    """
    An object used by RadioFieldRenderer that represents a single
    <input type='radio'>.
    """

    def __init__(self, name, value, attrs, choice, index):
        self.name, self.value = name, value
        self.attrs = attrs
        self.choice_value = force_unicode(choice[0])
        self.choice_label = force_unicode(choice[1])
        self.index = index

    def __unicode__(self):
        if 'id' in self.attrs:
            label_for = ' for="%s_%s"' % (self.attrs['id'], self.index)
        else:
            label_for = ''
        choice_label = conditional_escape(force_unicode(self.choice_label))
        return mark_safe(u'<label%s>%s %s</label>' % (label_for, self.tag(), choice_label))

    def is_checked(self):
        return self.value == self.choice_value

    def tag(self):
        if 'id' in self.attrs:
            self.attrs['id'] = '%s_%s' % (self.attrs['id'], self.index)
        final_attrs = dict(self.attrs, type='radio', name=self.name, value=self.choice_value)
        if self.is_checked():
            final_attrs['checked'] = 'checked'
        return mark_safe(u'<input%s />' % flatatt(final_attrs))

class RadioFieldRenderer(StrAndUnicode):
    """
    An object used by RadioSelect to enable customization of radio widgets.
    """

    def __init__(self, name, value, attrs, choices):
        import warnings
        warnings.warn(("renderers are deprecated: use templates to alter "
                       "widget rendering"), PendingDeprecationWarning)
        self.name, self.value, self.attrs = name, value, attrs
        self.choices = choices

    def __iter__(self):
        for i, choice in enumerate(self.choices):
            yield RadioInput(self.name, self.value, self.attrs.copy(), choice, i)

    def __getitem__(self, idx):
        choice = self.choices[idx] # Let the IndexError propogate
        return RadioInput(self.name, self.value, self.attrs.copy(), choice, idx)

    def __unicode__(self):
        return self.render()

    def render(self):
        """Outputs a <ul> for this set of radio fields."""
        return mark_safe(u'<ul>\n%s\n</ul>' % u'\n'.join([u'<li>%s</li>'
                % force_unicode(w) for w in self]))


class RadioSelect(Select):
    template_name = 'forms/widgets/radio.html'

    def __init__(self, *args, **kwargs):
        # Override the default renderer if we were passed one.
        renderer = kwargs.pop('renderer', None)
        if renderer:
            import warnings
            warnings.warn(("The renderer attribute is deprecated: use a "
                           "custom template to alter the widget rendering"),
                          DeprecationWarning)
        super(RadioSelect, self).__init__(*args, **kwargs)

    def get_renderer(self, name, value, attrs=None, choices=()):
        """Returns an instance of the renderer."""
        import warnings
        warnings.warn(("get_renderer is deprecated: use a custom template to "
                       "alter the widget rendering"),
                      DeprecationWarning)
        if value is None: value = ''
        str_value = force_unicode(value) # Normalize to string.
        final_attrs = self.build_attrs(attrs)
        choices = list(chain(self.choices, choices))
        return RadioFieldRenderer(name, str_value, final_attrs, choices)

    def id_for_label(self, id_):
        # RadioSelect is represented by multiple <input type="radio"> fields,
        # each of which has a distinct ID. The IDs are made distinct by a "_X"
        # suffix, where X is the zero-based index of the radio field. Thus,
        # the label for a RadioSelect should reference the first one ('_0').
        if id_:
            id_ += '_0'
        return id_
    id_for_label = classmethod(id_for_label)


class CheckboxSelectMultiple(SelectMultiple):
    template_name = 'forms/widgets/checkbox_select.html'

    def id_for_label(self, id_):
        # See the comment for RadioSelect.id_for_label()
        if id_:
            id_ += '_0'
        return id_
    id_for_label = classmethod(id_for_label)


class MultiWidget(Widget):
    """
    A widget that is composed of multiple widgets.

    Its render() method is different than other widgets', because it has to
    figure out how to split a single value for display in multiple widgets.
    The ``value`` argument can be one of two things:

        * A list.
        * A normal value (e.g., a string) that has been "compressed" from
          a list of values.

    In the second case -- i.e., if the value is NOT a list -- render() will
    first "decompress" the value into a list before rendering it. It does so by
    calling the decompress() method, which MultiWidget subclasses must
    implement. This method takes a single "compressed" value and returns a
    list.

    When render() does its HTML rendering, each value in the list is rendered
    with the corresponding widget -- the first value is rendered in the first
    widget, the second value is rendered in the second widget, etc.

    You'll probably want to use this class with MultiValueField.
    """
    template_name = 'forms/widgets/multiwidget.html'

    def __init__(self, widgets, attrs=None, template_name=None):
        self.widgets = [isinstance(w, type) and w() or w for w in widgets]
        super(MultiWidget, self).__init__(
            attrs=attrs, template_name=template_name)

    def get_context(self, name, value, attrs=None, extra_context=None, context_instance=None):
        if self.is_localized:
            for widget in self.widgets:
                widget.is_localized = self.is_localized
        # value is a list of values, each corresponding to a widget
        # in self.widgets.
        if not isinstance(value, list):
            value = self.decompress(value)
        output = []
        final_attrs = self.build_attrs(attrs)
        id_ = final_attrs.get('id', None)
        for i, widget in enumerate(self.widgets):
            try:
                widget_value = value[i]
            except IndexError:
                widget_value = None
            if id_:
                final_attrs = dict(final_attrs, id='%s_%s' % (id_, i))
            output.append(widget.render(name + '_%s' % i, widget_value, attrs=final_attrs))
        if context_instance is None:
            ctx = Context({'widgets': output})
        else:
            ctx = context_instance
            ctx.update({'widgets': output})
        ctx.update(self.get_context_data())
        if extra_context is not None:
            ctx.update(extra_context)
        return ctx

    def render(self, name, value, attrs=None, **kwargs):
        if hasattr(self, 'format_output'):
            import warnings
            warnings.warn(("format_output() is deprecated: use templates "
                           "to alter MultiWidget rendering"),
                          DeprecationWarning)
        return super(MultiWidget, self).render(
            name, value, attrs=attrs, **kwargs)

    def id_for_label(self, id_):
        # See the comment for RadioSelect.id_for_label()
        if id_:
            id_ += '_0'
        return id_
    id_for_label = classmethod(id_for_label)

    def value_from_datadict(self, data, files, name):
        return [widget.value_from_datadict(data, files, name + '_%s' % i) for i, widget in enumerate(self.widgets)]

    def _has_changed(self, initial, data):
        if initial is None:
            initial = [u'' for x in range(0, len(data))]
        else:
            if not isinstance(initial, list):
                initial = self.decompress(initial)
        for widget, initial, data in zip(self.widgets, initial, data):
            if widget._has_changed(initial, data):
                return True
        return False

    def decompress(self, value):
        """
        Returns a list of decompressed values for the given compressed value.
        The given value can be assumed to be valid, but not necessarily
        non-empty.
        """
        raise NotImplementedError('Subclasses must implement this method.')

    def _get_media(self):
        "Media for a multiwidget is the combination of all media of the subwidgets"
        media = Media()
        for w in self.widgets:
            media = media + w.media
        return media
    media = property(_get_media)

    def __deepcopy__(self, memo):
        obj = super(MultiWidget, self).__deepcopy__(memo)
        obj.widgets = copy.deepcopy(self.widgets)
        return obj


class SplitDateTimeWidget(MultiWidget):
    """
    A Widget that splits datetime input into two <input type="text"> boxes.
    """

    def __init__(self, attrs=None, date_format=None, time_format=None, template_name=None ):
        widgets = (DateInput(attrs=attrs, format=date_format),
                   TimeInput(attrs=attrs, format=time_format))
        super(SplitDateTimeWidget, self).__init__(
            widgets, attrs=attrs, template_name=template_name)

    def decompress(self, value):
        if value:
            return [value.date(), value.time().replace(microsecond=0)]
        return [None, None]


class SplitHiddenDateTimeWidget(SplitDateTimeWidget):
    """
    A Widget that splits datetime input into two <input type="hidden"> inputs.
    """
    is_hidden = True

    def __init__(self, attrs=None, date_format=None, time_format=None, template_name=None):
        super(SplitHiddenDateTimeWidget, self).__init__(
            attrs=attrs, template_name=template_name,
            date_format=date_format, time_format=time_format)
        for widget in self.widgets:
            widget.input_type = 'hidden'
            widget.is_hidden = True
