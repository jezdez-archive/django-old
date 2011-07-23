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


class LayoutTests(TestCase):
    def test_default_layout_is_same_as_p_layout(self):
        form = RegistrationForm()
        default = render('{% form form %}', {'form': form})
        p = render('{% form form using "forms/layouts/p.html" %}', {'form': form})
        self.assertEqual(default, p)

    def test_p_layout(self):
        form = RegistrationForm()
        p = render('{% form form using "forms/layouts/p.html" %}', {'form': form})
        self.assertHTMLEqual(p, '''
        <p><label for="id_firstname">Your first name?</label> <input type="text" name="firstname" id="id_firstname" /></p>
        <p><label for="id_lastname">Your last name:</label> <input type="text" name="lastname" id="id_lastname" /></p>
        <p><label for="id_username">Username:</label> <input type="text" name="username" id="id_username" maxlength="30" /></p>
        <p>
            <label for="id_password">Password:</label> <input type="password" name="password" id="id_password" />
            <span class="helptext">Make sure to use a secure password.</span>
        </p>
        <p><label for="id_password2">Retype password:</label> <input type="password" name="password2" id="id_password2" /></p>
        <p><label for="id_age">Age:</label> <input type="text" name="age" id="id_age" /></p>
        <input type="hidden" name="honeypot" id="id_honeypot" />
        ''')

    def test_p_layout_with_errors(self):
        form = RegistrationForm({'non_field_errors': True})
        p = render('{% form form using "forms/layouts/p.html" %}', {'form': form})
        self.assertHTMLEqual(p, '''
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
        <p><label for="id_age">Age:</label> <input type="text" name="age" id="id_age" /></p>
        <input type="hidden" name="honeypot" id="id_honeypot" />
        ''')

        form = RegistrationForm({'non_field_errors': True, 'honeypot': 1})
        p = render('{% form form using "forms/layouts/p.html" %}', {'form': form})
        self.assertHTMLEqual(p, '''
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
        <p><label for="id_age">Age:</label> <input type="text" name="age" id="id_age" /></p>
        <input type="hidden" name="honeypot" id="id_honeypot" value="1" />
        ''')

    def test_p_layout_with_custom_label(self):
        form = OneFieldForm()
        p = render('''
            {% form form using %}
                {% formrow form.text using "forms/rows/p.html" with label="Custom label" %}
            {% endform %}
        ''', {'form': form})
        self.assertHTMLEqual(p, '''
        <p><label for="id_text">Custom label:</label> <input type="text" name="text" id="id_text" /></p>
        ''')

    def test_p_layout_with_custom_help_text(self):
        form = OneFieldForm()
        p = render('''
            {% form form using %}
                {% formrow form.text using "forms/rows/p.html" with help_text="Would you mind entering text here?" %}
            {% endform %}
        ''', {'form': form})
        self.assertHTMLEqual(p, '''
        <p>
            <label for="id_text">Text:</label> <input type="text" name="text" id="id_text" />
            <span class="helptext">Would you mind entering text here?</span>
        </p>
        ''')
