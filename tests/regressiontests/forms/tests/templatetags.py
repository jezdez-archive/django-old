from django import forms
from django.template import Context, Template, TemplateSyntaxError
from django.test import TestCase


def render(template, context=None):
    if context is None:
        context = {}
    c = Context(context)
    t = Template(template)
    return t.render(c)


class SimpleForm(forms.Form):
    name = forms.CharField()


class PersonForm(forms.Form):
    firstname = forms.CharField()
    lastname = forms.CharField()
    age = forms.IntegerField()


class FormTagTests(TestCase):
    def test_valid_syntax(self):
        render('{% form myform %}')
        render('{% form myform using "myform_layout.html" %}')
        render('{% form myform secondform %}')
        render('{% form myform using %}{% endform %}')
        render('{% form myform secondform using %}{% endform %}')
        render('{% form myform secondform thirdform %}')

    def test_invalid_syntax(self):
        with self.assertRaises(TemplateSyntaxError):
            render('{% form %}')
        with self.assertRaises(TemplateSyntaxError):
            render('{% form using %}')
        with self.assertRaises(TemplateSyntaxError):
            render('{% form using %}{% endform %}')
        with self.assertRaises(TemplateSyntaxError):
            render('{% form myform using "myform_layout.html" too_many_arguments %}')
        with self.assertRaises(TemplateSyntaxError):
            render('{% form myform %}{% endform %}')
        with self.assertRaises(TemplateSyntaxError):
            render('{% form myform using "myform_layout.html" %}{% endform %}')

    def test_inline_content(self):
        self.assertHTMLEqual(
            render('{% form myform using %}foo{% endform %}'),
            'foo')
        self.assertHTMLEqual(render('''
            {% form myform using %}
                {% if 1 %}True{% else %}False{% endif %}
            {% endform %}
            '''), 'True')
        # don't leak variables into outer scope
        self.assertHTMLEqual(render('''
            {% form myform using %}
                <ins>{% cycle "foo" "bar" as value %}</ins>
            {% endform %}
            <del>{{ value }}</del>
            '''), '<ins>foo</ins><del />')
        # form variable equals the first argument in form tag
        self.assertHTMLEqual(render('''
            {% form myform using %}{% if myform == form %}Equals!{% endif %}{% endform %}
            ''', {'myform': SimpleForm()}), 'Equals!')
        self.assertHTMLEqual(render('''
            {% form f1 f2 using %}
                {% if f1 == forms.0 and f2 == forms.1 and f1 != f2 %}
                    Equals!
                {% endif %}
            {% endform %}
            ''', {'f1': SimpleForm(), 'f2': SimpleForm()}), 'Equals!')
        # none forms are not included in form list
        self.assertHTMLEqual(render('''
            {% form f1 nothing f2 more_of_nothing using %}
                {% if f1 == forms.0 and f2 == forms.1 %}
                {% if forms.2 == None and more_of_nothing == None %}
                    Equals!
                {% endif %}
                {% endif %}
                Length: {{ forms|length }}
            {% endform %}''', {
                'f1': SimpleForm(),
                'f2': SimpleForm()
            }), 'Equals! Length: 2')

    def test_include_content(self):
        self.assertHTMLEqual(
            render('{% form myform using "simple_form_tag.html" %}', {
                'myform': PersonForm(),
            }), '''
            Forms: 1
            1. Form Fields: firstname lastname age
            ''')
        self.assertHTMLEqual(
            render('{% form f1 non f2 using "simple_form_tag.html" %}', {
                'f1': SimpleForm(),
                'f2': PersonForm(),
            }), '''
            Forms: 2
            1. Form Fields: name
            2. Form Fields: firstname lastname age
            ''')
