from django import forms
from django.forms import widgets
from django.template.formtags import Fieldname, Fieldtype, FormConfig
from django.test import TestCase


class RegistrationForm(forms.Form):
    name = forms.CharField(label='First- and Lastname', max_length=50)
    email = forms.EmailField(max_length=50,
        help_text='Please enter a valid email.')
    short_biography = forms.CharField(max_length=200)
    comment = forms.CharField(widget=widgets.Textarea)


class FormConfigTests(TestCase):
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

    def test_retrieve_for_multiple_valid_values(self):
        form = RegistrationForm()
        config = FormConfig()

        config.configure('widget', widgets.Textarea(),
            filter=Fieldtype(forms.CharField))
        config.configure('widget', widgets.HiddenInput(),
            filter=Fieldname('short_biography'))

        widget = config.retrieve('widget', bound_field=form['name'])
        self.assertEqual(widget.__class__, widgets.Textarea)
        widget = config.retrieve('widget', bound_field=form['comment'])
        self.assertEqual(widget.__class__, widgets.Textarea)

        # we get HiddenInput since this was configured last, even the Textarea
        # config applies to ``short_biography``
        widget = config.retrieve('widget', bound_field=form['short_biography'])
        self.assertEqual(widget.__class__, widgets.HiddenInput)

    def test_stacked_config(self):
        form = RegistrationForm()
        config = FormConfig()

        config.push()
        config.configure('widget', widgets.Textarea(),
            filter=Fieldtype(forms.CharField))

        config.push()
        config.configure('widget', widgets.HiddenInput(),
            filter=Fieldname('short_biography'))

        widget = config.retrieve('widget', bound_field=form['short_biography'])
        self.assertEqual(widget.__class__, widgets.HiddenInput)

        config.pop()
        widget = config.retrieve('widget', bound_field=form['short_biography'])
        self.assertEqual(widget.__class__, widgets.Textarea)

        config.pop()
        widget = config.retrieve('widget', bound_field=form['short_biography'])
        self.assertEqual(widget.__class__, widgets.TextInput)
