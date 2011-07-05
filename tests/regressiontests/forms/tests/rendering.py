from django import forms
from django.forms import widgets
from django.test import TestCase


class Fieldname(object):
    def __init__(self, name):
        self.name = name

    def __call__(self, bound_field):
        if bound_field:
            return bound_field.name == self.name
        return False


def default_label(bound_field, **kwargs):
    if bound_field:
        return bound_field.label


def default_help_text(bound_field, **kwargs):
    if bound_field:
        return bound_field.field.help_text


def default_widget(bound_field, **kwargs):
    if bound_field:
        return bound_field.field.widget


class FormConfig(object):
    defaults = {
        'layout': lambda **kwargs: 'forms/layouts/default.html',
        'rowtemplate': lambda **kwargs: 'forms/rows/default.html',
        'label': default_label,
        'help_text': default_help_text,
        'widget': default_widget,
    }

    def __init__(self):
        self._reset_dicts()

    def _reset_dicts(self, value=None):
        self.dicts = [value or {}]

    def configure(self, key, value, filter=None):
        '''
        key: Key under which ``value`` can be retrieved.
        value: value that is returned if retrieve is called with the same key
        '''
        if filter is None:
            filter = lambda **kwargs: True
        self.dicts[-1][key] = (value, filter)

    def retrieve(self, key, **kwargs):
        '''
        key: Key to lookup in key-value store
        **kwargs: A dictionary of kwargs that will be passed into the filters
        of all found values. So the latest added value for key will be
        retrieved. If the value has a ``filter`` attached, then ``filter``
        will be called with ``kwargs``. Value will re returned if ``filter``
        returned ``True``. Otherwise the next available value will be looked
        up.

        If no value is found: return ``self.defaults[key](**kwargs)``
        '''
        for d in reversed(self.dicts):
            if key in d:
                value, filter = d[key]
                if filter(**kwargs):
                    return value

        if key not in self.defaults:
            return None
        return self.defaults[key](**kwargs)


class RegistrationForm(forms.Form):
    name = forms.CharField(label='First- and Lastname', max_length=50)
    email = forms.EmailField(max_length=50,
        help_text='Please enter a valid email.')
    comment = forms.CharField(max_length=50, widget=widgets.Textarea)


class FormConfigTests(TestCase):
    '''
    What we want to accomplish:

    * Render multiple forms
    * Manipulate forms based on a generic config
    * Config for:
        + individual fields
        + field types
        + field names
    * Config must be mutable
    * ... and maybe stackbased scope
    '''

    def test_default_retrieve(self):
        '''
        Test if FormConfig returns the correct default values if no
        configuration was made.
        '''
        form = RegistrationForm()
        config = FormConfig()

        # retrieve widget

        widget = config.retrieve('widget', bound_field=form['name'])
        self.assertTrue(isinstance(widget, widgets.TextInput))
        self.assertEqual(widget, form.fields['name'].widget)

        widget = config.retrieve('widget', bound_field=form['comment'])
        self.assertTrue(isinstance(widget, widgets.Textarea))
        self.assertEqual(widget, form.fields['comment'].widget)

        # retrieve label

        label = config.retrieve('label', bound_field=form['email'])
        self.assertEqual(label, 'Email')

        label = config.retrieve('label', bound_field=form['name'])
        self.assertEqual(label, 'First- and Lastname')

        # retrieve help text

        help_text = config.retrieve('help_text', bound_field=form['name'])
        self.assertFalse(help_text)

        help_text = config.retrieve('help_text', bound_field=form['email'])
        self.assertEqual(help_text, 'Please enter a valid email.')

        # retrieve row template

        template = config.retrieve('rowtemplate', fields=(form['name'], form['email'],))
        self.assertEqual(template, 'forms/rows/default.html')

        # retrieve form layout

        template = config.retrieve('layout', forms=(form,))
        self.assertEqual(template, 'forms/layouts/default.html')

    def test_configure_and_retrieve(self):
        form = RegistrationForm()

        config = FormConfig()
        widget = config.retrieve('widget', bound_field=form['comment'])
        self.assertEqual(widget.__class__, widgets.Textarea)

        config.configure('widget', widgets.TextInput(), filter=Fieldname('comment'))

        widget = config.retrieve('widget', bound_field=form['comment'])
        self.assertEqual(widget.__class__, widgets.TextInput)

        widget = config.retrieve('widget', bound_field=form['name'])
        self.assertEqual(widget.__class__, widgets.TextInput)
