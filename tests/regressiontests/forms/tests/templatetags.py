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
        render('{% form myform secondform thirdform using "myform_layout.html" with arg=value %}')
        render('{% form myform secondform thirdform using "myform_layout.html" only %}')
        render('{% form myform secondform thirdform using "myform_layout.html" with arg=value only %}')

    def test_invalid_syntax(self):
        with self.assertRaises(TemplateSyntaxError):
            render('{% form %}')
        with self.assertRaises(TemplateSyntaxError):
            render('{% form using %}')
        with self.assertRaises(TemplateSyntaxError):
            render('{% form myform using "myform_layout.html" with %}')
        with self.assertRaises(TemplateSyntaxError):
            render('{% form myform using "myform_layout.html" with only %}')
        with self.assertRaises(TemplateSyntaxError):
            render('{% form myform using "myform_layout.html" only with arg=value %}')
        with self.assertRaises(TemplateSyntaxError):
            render('{% form using %}{% endform %}')
        with self.assertRaises(TemplateSyntaxError):
            render('{% form myform using "myform_layout.html" too_many_arguments %}')
        with self.assertRaises(TemplateSyntaxError):
            render('{% form myform %}{% endform %}')
        with self.assertRaises(TemplateSyntaxError):
            render('{% form myform using "myform_layout.html" %}{% endform %}')
        with self.assertRaises(TemplateSyntaxError):
            render('{% form myform using "myform_layout.html" only %}{% endform %}')
        with self.assertRaises(TemplateSyntaxError):
            render('{% form myform using "myform_layout.html" with arg=value %}{% endform %}')

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
        with self.assertTemplateUsed('simple_form_tag.html'):
            self.assertHTMLEqual(
                render('{% form myform using "simple_form_tag.html" %}', {
                    'myform': PersonForm(),
                }), '''
                Forms: 1
                1. Form Fields: firstname lastname age
                ''')
        with self.assertTemplateUsed('simple_form_tag.html'):
            self.assertHTMLEqual(
                render('{% form f1 non f2 using "simple_form_tag.html" %}', {
                    'f1': SimpleForm(),
                    'f2': PersonForm(),
                }), '''
                Forms: 2
                1. Form Fields: name
                2. Form Fields: firstname lastname age
                ''')

    def test_include_content_with_extra_arguments(self):
        with self.assertTemplateUsed('simple_form_tag.html'):
            self.assertHTMLEqual(
                render('{% form myform using "simple_form_tag.html" with extra_argument="spam" %}', {
                    'myform': PersonForm(),
                }), '''
                Forms: 1
                1. Form Fields: firstname lastname age
                Extra argument: spam
                ''')
        with self.assertTemplateUsed('simple_form_tag.html'):
            self.assertHTMLEqual(
                render('{% form myform using "simple_form_tag.html" with extra_argument=0 %}', {
                    'myform': PersonForm(),
                }), '''
                Forms: 1
                1. Form Fields: firstname lastname age
                ''')
        with self.assertTemplateUsed('simple_form_tag.html'):
            self.assertHTMLEqual(
                render('''
                    {% with extra_argument="ham" %}
                        {% form myform using "simple_form_tag.html" %}
                    {% endwith %}
                    ''', {'myform': PersonForm()}),
                '''
                Forms: 1
                1. Form Fields: firstname lastname age
                Extra argument: ham
                ''')
        with self.assertTemplateUsed('simple_form_tag.html'):
            self.assertHTMLEqual(
                render('''
                    {% with extra_argument="ham" %}
                        {% form myform using "simple_form_tag.html" only %}
                    {% endwith %}
                    ''', {'myform': PersonForm()}),
                '''
                Forms: 1
                1. Form Fields: firstname lastname age
                ''')
        with self.assertTemplateUsed('simple_form_tag.html'):
            self.assertHTMLEqual(
                render('''
                    {% with extra_argument="spam" %}
                        {% form myform using "simple_form_tag.html" with extra_argument=0 %}
                    {% endwith %}
                    ''', {'myform': PersonForm()}),
                '''
                Forms: 1
                1. Form Fields: firstname lastname age
                ''')

    def test_default_template(self):
        with self.assertTemplateUsed('forms/layouts/default.html'):
            render('{% form myform %}')


class FormRowTagTests(TestCase):
    def test_valid_syntax(self):
        render('{% formrow myform.field %}')
        render('{% formrow myform.field using "myrow_layout.html" %}')
        render('{% formrow myform.field secondfield %}')
        render('{% formrow myform.field secondfield thirdfield %}')
        render('{% formrow myform.field secondfield thirdfield using "myform_layout.html" with arg=value %}')
        render('{% formrow myform.field secondfield thirdfield using "myform_layout.html" only %}')
        render('{% formrow myform.field secondfield thirdfield using "myform_layout.html" with arg=value only %}')

    def test_invalid_syntax(self):
        with self.assertRaises(TemplateSyntaxError):
            render('{% formrow %}')
        with self.assertRaises(TemplateSyntaxError):
            render('{% formrow using %}')
        with self.assertRaises(TemplateSyntaxError):
            render('{% formrow myform.name using %}')
        with self.assertRaises(TemplateSyntaxError):
            render('{% formrow myform.name using "myform_layout.html" with %}')
        with self.assertRaises(TemplateSyntaxError):
            render('{% formrow myform.name using "myform_layout.html" with only %}')
        with self.assertRaises(TemplateSyntaxError):
            render('{% formrow myform.name using "myform_layout.html" only with arg=value %}')
        with self.assertRaises(TemplateSyntaxError):
            render('{% formrow myform.name using "myform_layout.html" too_many_arguments %}')
        with self.assertRaises(TemplateSyntaxError):
            render('{% formrow myform.name using %}{% endformrow %}')
        with self.assertRaises(TemplateSyntaxError):
            render('{% formrow myform.name using %}{% endform %}')

    def test_include_content(self):
        with self.assertTemplateUsed('simple_formrow_tag.html'):
            self.assertHTMLEqual(
                render('{% formrow myform.lastname using "simple_formrow_tag.html" %}', {
                    'myform': PersonForm(),
                }), '''
                Fields: 1
                1. Field: lastname
                ''')
        with self.assertTemplateUsed('simple_formrow_tag.html'):
            self.assertHTMLEqual(
                render('{% formrow person.age simple.non simple.name using "simple_formrow_tag.html" %}', {
                    'simple': SimpleForm(),
                    'person': PersonForm(),
                }), '''
                Fields: 2
                1. Field: age
                2. Field: name
                ''')

    def test_include_content_with_extra_arguments(self):
        with self.assertTemplateUsed('simple_formrow_tag.html'):
            self.assertHTMLEqual(
                render('{% formrow myform.firstname using "simple_formrow_tag.html" with extra_argument="spam" %}', {
                    'myform': PersonForm(),
                }), '''
                Fields: 1
                1. Field: firstname
                Extra argument: spam
                ''')
        with self.assertTemplateUsed('simple_formrow_tag.html'):
            self.assertHTMLEqual(
                render('{% formrow myform.age using "simple_formrow_tag.html" with extra_argument=0 %}', {
                    'myform': PersonForm(),
                }), '''
                Fields: 1
                1. Field: age
                ''')
        with self.assertTemplateUsed('simple_formrow_tag.html'):
            self.assertHTMLEqual(
                render('''
                    {% with extra_argument="ham" %}
                        {% formrow myform.lastname using "simple_formrow_tag.html" %}
                    {% endwith %}
                    ''', {'myform': PersonForm()}),
                '''
                Fields: 1
                1. Field: lastname
                Extra argument: ham
                ''')
        with self.assertTemplateUsed('simple_formrow_tag.html'):
            self.assertHTMLEqual(
                render('''
                    {% with extra_argument="ham" %}
                        {% formrow myform.firstname using "simple_formrow_tag.html" only %}
                    {% endwith %}
                    ''', {'myform': PersonForm()}),
                '''
                Fields: 1
                1. Field: firstname
                ''')
        with self.assertTemplateUsed('simple_formrow_tag.html'):
            self.assertHTMLEqual(
                render('''
                    {% with extra_argument="spam" %}
                        {% formrow myform.firstname using "simple_formrow_tag.html" with extra_argument=0 %}
                    {% endwith %}
                    ''', {'myform': PersonForm()}),
                '''
                Fields: 1
                1. Field: firstname
                ''')

    def test_default_template(self):
        with self.assertTemplateUsed('forms/rows/default.html'):
            render('{% formrow myform.name %}')
