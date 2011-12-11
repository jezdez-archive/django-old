from __future__ import with_statement

from django import forms
from django.core.exceptions import ValidationError
from django.template import Context, Template
from django.test import TestCase
from django.utils.translation import ugettext_lazy as _


def render(template, context=None):
    if context is None:
        context = {}
    c = Context(context)
    t = Template(template)
    return t.render(c)


class OneFieldForm(forms.Form):
    text = forms.CharField()

    def clean(self):
        if self.errors:
            raise ValidationError(u'Please correct the errors below.')


class RegistrationForm(forms.Form):
    honeypot = forms.CharField(required=False, widget=forms.HiddenInput)
    firstname = forms.CharField(label=_(u'Your first name?'))
    lastname = forms.CharField(label=_(u'Your last name:'))
    username = forms.CharField(max_length=30)
    password = forms.CharField(widget=forms.PasswordInput,
        help_text=_(u'Make sure to use a secure password.'))
    password2 = forms.CharField(label=_(u'Retype password'), widget=forms.PasswordInput)
    age = forms.IntegerField(required=False)

    def clean_honeypot(self):
        if self.cleaned_data.get('honeypot'):
            raise ValidationError(u'Haha, you trapped into the honeypot.')
        return self.cleaned_data['honeypot']

    def clean(self):
        if self.errors:
            raise ValidationError(u'Please correct the errors below.')


class PLayoutTests(TestCase):
    def test_default_layout_is_same_as_p_layout(self):
        form = RegistrationForm()
        default = render('{% form form %}', {'form': form})
        layout = render('{% form form using "forms/layouts/p.html" %}', {'form': form})
        self.assertEqual(default, layout)

    def test_layout(self):
        form = RegistrationForm()
        with self.assertTemplateUsed('forms/layouts/p.html'):
            with self.assertTemplateUsed('forms/rows/p.html'):
                layout = render('{% form form using "forms/layouts/p.html" %}', {'form': form})
        self.assertHTMLEqual(layout, '''
        <p><label for="id_firstname">Your first name?</label> <input type="text" name="firstname" id="id_firstname" />
        </p>
        <p><label for="id_lastname">Your last name:</label> <input type="text" name="lastname" id="id_lastname" />
        </p>
        <p><label for="id_username">Username:</label> <input type="text" name="username" id="id_username" maxlength="30" />
        </p>
        <p><label for="id_password">Password:</label> <input type="password" name="password" id="id_password" />
         <span class="helptext">Make sure to use a secure password.</span></p>
        <p><label for="id_password2">Retype password:</label> <input type="password" name="password2" id="id_password2" />
        </p>
        <p><label for="id_age">Age:</label> <input type="text" name="age" id="id_age" />
        <input type="hidden" name="honeypot" id="id_honeypot" />
        </p>
        ''')

    def test_layout_with_errors(self):
        form = RegistrationForm({'non_field_errors': True})
        layout = render('{% form form using "forms/layouts/p.html" %}', {'form': form})
        self.assertHTMLEqual(layout, '''
        <ul class="errorlist"><li>Please correct the errors below.</li></ul>
        <ul class="errorlist"><li>This field is required.</li></ul>
        <p><label for="id_firstname">Your first name?</label> <input type="text" name="firstname" id="id_firstname" /></p>
        <ul class="errorlist"><li>This field is required.</li></ul>
        <p><label for="id_lastname">Your last name:</label> <input type="text" name="lastname" id="id_lastname" /></p>
        <ul class="errorlist"><li>This field is required.</li></ul>
        <p><label for="id_username">Username:</label> <input type="text" name="username" id="id_username" maxlength="30" /></p>
        <ul class="errorlist"><li>This field is required.</li></ul>
        <p>
            <label for="id_password">Password:</label> <input type="password" name="password" id="id_password" />
            <span class="helptext">Make sure to use a secure password.</span>
        </p>
        <ul class="errorlist"><li>This field is required.</li></ul>
        <p><label for="id_password2">Retype password:</label> <input type="password" name="password2" id="id_password2" /></p>
        <p><label for="id_age">Age:</label> <input type="text" name="age" id="id_age" />
            <input type="hidden" name="honeypot" id="id_honeypot" /></p>
        ''')

        form = RegistrationForm({'non_field_errors': True, 'honeypot': 1})
        layout = render('{% form form using "forms/layouts/p.html" %}', {'form': form})
        self.assertHTMLEqual(layout, '''
        <ul class="errorlist">
            <li>Please correct the errors below.</li>
            <li>Haha, you trapped into the honeypot.</li>
        </ul>
        <ul class="errorlist"><li>This field is required.</li></ul>
        <p><label for="id_firstname">Your first name?</label> <input type="text" name="firstname" id="id_firstname" /></p>
        <ul class="errorlist"><li>This field is required.</li></ul>
        <p><label for="id_lastname">Your last name:</label> <input type="text" name="lastname" id="id_lastname" /></p>
        <ul class="errorlist"><li>This field is required.</li></ul>
        <p><label for="id_username">Username:</label> <input type="text" name="username" id="id_username" maxlength="30" /></p>
        <ul class="errorlist"><li>This field is required.</li></ul>
        <p>
            <label for="id_password">Password:</label> <input type="password" name="password" id="id_password" />
            <span class="helptext">Make sure to use a secure password.</span>
        </p>
        <ul class="errorlist"><li>This field is required.</li></ul>
        <p><label for="id_password2">Retype password:</label> <input type="password" name="password2" id="id_password2" /></p>
        <p><label for="id_age">Age:</label> <input type="text" name="age" id="id_age" />
            <input type="hidden" name="honeypot" id="id_honeypot" value="1" /></p>
        ''')

    def test_layout_with_custom_label(self):
        form = OneFieldForm()
        layout = render('''
            {% form form using %}
                {% formrow form.text using "forms/rows/p.html" with label="Custom label" %}
            {% endform %}
        ''', {'form': form})
        self.assertHTMLEqual(layout, '''
        <p><label for="id_text">Custom label:</label> <input type="text" name="text" id="id_text" /></p>
        ''')

    def test_layout_with_custom_help_text(self):
        form = OneFieldForm()
        layout = render('''
            {% form form using %}
                {% formrow form.text using "forms/rows/p.html" with help_text="Would you mind entering text here?" %}
            {% endform %}
        ''', {'form': form})
        self.assertHTMLEqual(layout, '''
        <p>
            <label for="id_text">Text:</label> <input type="text" name="text" id="id_text" />
            <span class="helptext">Would you mind entering text here?</span>
        </p>
        ''')


class TableLayoutTests(TestCase):
    def test_layout(self):
        form = RegistrationForm()
        with self.assertTemplateUsed('forms/layouts/table.html'):
            with self.assertTemplateUsed('forms/rows/tr.html'):
                layout = render('{% form form using "forms/layouts/table.html" %}', {'form': form})
        self.assertHTMLEqual(layout, '''
        <tr><th><label for="id_firstname">Your first name?</label></th><td><input type="text" name="firstname" id="id_firstname" /></td></tr>
        <tr><th><label for="id_lastname">Your last name:</label></th><td><input type="text" name="lastname" id="id_lastname" /></td></tr>
        <tr><th><label for="id_username">Username:</label></th><td><input type="text" name="username" id="id_username" maxlength="30" /></td></tr>
        <tr><th>
            <label for="id_password">Password:</label></th><td><input type="password" name="password" id="id_password" />
            <br /><span class="helptext">Make sure to use a secure password.</span></td></tr>
        <tr><th><label for="id_password2">Retype password:</label></th><td><input type="password" name="password2" id="id_password2" /></td></tr>
        <tr><th>
            <label for="id_age">Age:</label></th><td><input type="text" name="age" id="id_age" />
            <input type="hidden" name="honeypot" id="id_honeypot" />
        </td></tr>
        ''')

    def test_layout_with_errors(self):
        form = RegistrationForm({'non_field_errors': True})
        layout = render('{% form form using "forms/layouts/table.html" %}', {'form': form})
        self.assertHTMLEqual(layout, '''
        <tr><td colspan="2"><ul class="errorlist"><li>Please correct the errors below.</li></ul></td></tr>
        <tr><th><label for="id_firstname">Your first name?</label></th><td><ul class="errorlist"><li>This field is required.</li></ul><input type="text" name="firstname" id="id_firstname" /></td></tr>
        <tr><th><label for="id_lastname">Your last name:</label></th><td><ul class="errorlist"><li>This field is required.</li></ul><input type="text" name="lastname" id="id_lastname" /></td></tr>
        <tr><th><label for="id_username">Username:</label></th><td><ul class="errorlist"><li>This field is required.</li></ul><input type="text" name="username" id="id_username" maxlength="30" /></td></tr>
        <tr>
            <th><label for="id_password">Password:</label></th>
            <td>
                <ul class="errorlist"><li>This field is required.</li></ul>
                <input type="password" name="password" id="id_password" />
                <br /><span class="helptext">Make sure to use a secure password.</span>
            </td>
        </tr>
        <tr>
            <th><label for="id_password2">Retype password:</label></th>
            <td><ul class="errorlist"><li>This field is required.</li></ul><input type="password" name="password2" id="id_password2" /></td>
        </tr>
        <tr><th><label for="id_age">Age:</label></th><td><input type="text" name="age" id="id_age" />
            <input type="hidden" name="honeypot" id="id_honeypot" /></td></tr>
        ''')

        form = RegistrationForm({'non_field_errors': True, 'honeypot': 1})
        layout = render('{% form form using "forms/layouts/table.html" %}', {'form': form})
        self.assertHTMLEqual(layout, '''
        <tr><td colspan="2"><ul class="errorlist"><li>Please correct the errors below.</li><li>Haha, you trapped into the honeypot.</li></ul></td></tr>
        <tr><th><label for="id_firstname">Your first name?</label></th><td><ul class="errorlist"><li>This field is required.</li></ul><input type="text" name="firstname" id="id_firstname" /></td></tr>
        <tr><th><label for="id_lastname">Your last name:</label></th><td><ul class="errorlist"><li>This field is required.</li></ul><input type="text" name="lastname" id="id_lastname" /></td></tr>
        <tr><th><label for="id_username">Username:</label></th><td><ul class="errorlist"><li>This field is required.</li></ul><input type="text" name="username" id="id_username" maxlength="30" /></td></tr>
        <tr><th><label for="id_password">Password:</label></th><td><ul class="errorlist"><li>This field is required.</li></ul><input type="password" name="password" id="id_password" /><br /><span class="helptext">Make sure to use a secure password.</span></td></tr>
        <tr><th><label for="id_password2">Retype password:</label></th><td><ul class="errorlist"><li>This field is required.</li></ul><input type="password" name="password2" id="id_password2" /></td></tr>
        <tr><th><label for="id_age">Age:</label></th><td><input type="text" name="age" id="id_age" />
            <input type="hidden" name="honeypot" value="1" id="id_honeypot" /></td></tr>
        ''')

    def test_layout_with_custom_label(self):
        form = OneFieldForm()
        layout = render('''
            {% form form using %}
                {% formrow form.text using "forms/rows/tr.html" with label="Custom label" %}
            {% endform %}
        ''', {'form': form})
        self.assertHTMLEqual(layout, '''
        <tr><th><label for="id_text">Custom label:</label></th><td><input type="text" name="text" id="id_text" /></td></tr>
        ''')

    def test_layout_with_custom_help_text(self):
        form = OneFieldForm()
        layout = render('''
            {% form form using %}
                {% formrow form.text using "forms/rows/tr.html" with help_text="Would you mind entering text here?" %}
            {% endform %}
        ''', {'form': form})
        self.assertHTMLEqual(layout, '''
        <tr><th>
            <label for="id_text">Text:</label>
        </th><td>
            <input type="text" name="text" id="id_text" />
            <br /><span class="helptext">Would you mind entering text here?</span>
        </td></tr>
        ''')


class UlLayoutTests(TestCase):
    def test_layout(self):
        form = RegistrationForm()
        with self.assertTemplateUsed('forms/layouts/ul.html'):
            with self.assertTemplateUsed('forms/rows/li.html'):
                layout = render('{% form form using "forms/layouts/ul.html" %}', {'form': form})
        self.assertHTMLEqual(layout, '''
        <li><label for="id_firstname">Your first name?</label> <input type="text" name="firstname" id="id_firstname" /></li>
        <li><label for="id_lastname">Your last name:</label> <input type="text" name="lastname" id="id_lastname" /></li>
        <li><label for="id_username">Username:</label> <input type="text" name="username" id="id_username" maxlength="30" /></li>
        <li><label for="id_password">Password:</label> <input type="password" name="password" id="id_password" />
            <span class="helptext">Make sure to use a secure password.</span></li>
        <li><label for="id_password2">Retype password:</label> <input type="password" name="password2" id="id_password2" /></li>
        <li><label for="id_age">Age:</label> <input type="text" name="age" id="id_age" />
            <input type="hidden" name="honeypot" id="id_honeypot" /></li>
        ''')

    def test_layout_with_errors(self):
        form = RegistrationForm({'non_field_errors': True})
        layout = render('{% form form using "forms/layouts/ul.html" %}', {'form': form})
        self.maxDiff = None
        self.assertHTMLEqual(layout, '''
        <li><ul class="errorlist"><li>Please correct the errors below.</li></ul></li>
        <li><ul class="errorlist"><li>This field is required.</li></ul><label for="id_firstname">Your first name?</label> <input type="text" name="firstname" id="id_firstname" /></li>
        <li><ul class="errorlist"><li>This field is required.</li></ul><label for="id_lastname">Your last name:</label> <input type="text" name="lastname" id="id_lastname" /></li>
        <li><ul class="errorlist"><li>This field is required.</li></ul><label for="id_username">Username:</label> <input type="text" name="username" id="id_username" maxlength="30" /></li>
        <li><ul class="errorlist"><li>This field is required.</li></ul><label for="id_password">Password:</label> <input type="password" name="password" id="id_password" />
            <span class="helptext">Make sure to use a secure password.</span></li>
        <li><ul class="errorlist"><li>This field is required.</li></ul><label for="id_password2">Retype password:</label> <input type="password" name="password2" id="id_password2" /></li>
        <li><label for="id_age">Age:</label> <input type="text" name="age" id="id_age" />
            <input type="hidden" name="honeypot" id="id_honeypot" /></li>
        ''')

        form = RegistrationForm({'non_field_errors': True, 'honeypot': 1})
        layout = render('{% form form using "forms/layouts/ul.html" %}', {'form': form})
        self.assertHTMLEqual(layout, '''
        <li><ul class="errorlist"><li>Please correct the errors below.</li><li>Haha, you trapped into the honeypot.</li></ul></li>
        <li><ul class="errorlist"><li>This field is required.</li></ul><label for="id_firstname">Your first name?</label> <input type="text" name="firstname" id="id_firstname" /></li>
        <li><ul class="errorlist"><li>This field is required.</li></ul><label for="id_lastname">Your last name:</label> <input type="text" name="lastname" id="id_lastname" /></li>
        <li><ul class="errorlist"><li>This field is required.</li></ul><label for="id_username">Username:</label> <input type="text" name="username" id="id_username" maxlength="30" /></li>
        <li><ul class="errorlist"><li>This field is required.</li></ul><label for="id_password">Password:</label> <input type="password" name="password" id="id_password" />
            <span class="helptext">Make sure to use a secure password.</span></li>
        <li><ul class="errorlist"><li>This field is required.</li></ul><label for="id_password2">Retype password:</label> <input type="password" name="password2" id="id_password2" /></li>
        <li><label for="id_age">Age:</label> <input type="text" name="age" id="id_age" />
            <input type="hidden" name="honeypot" value="1" id="id_honeypot" /></li>
        ''')

    def test_layout_with_custom_label(self):
        form = OneFieldForm()
        layout = render('''
            {% form form using %}
                {% formrow form.text using "forms/rows/li.html" with label="Custom label" %}
            {% endform %}
        ''', {'form': form})
        self.assertHTMLEqual(layout, '''
        <li><label for="id_text">Custom label:</label><input type="text" name="text" id="id_text" /></li>
        ''')

    def test_layout_with_custom_help_text(self):
        form = OneFieldForm()
        layout = render('''
            {% form form using %}
                {% formrow form.text using "forms/rows/li.html" with help_text="Would you mind entering text here?" %}
            {% endform %}
        ''', {'form': form})
        self.assertHTMLEqual(layout, '''
        <li>
            <label for="id_text">Text:</label>
            <input type="text" name="text" id="id_text" />
            <span class="helptext">Would you mind entering text here?</span>
        </li>
        ''')
