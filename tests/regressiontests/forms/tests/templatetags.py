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
            render('{% form myform using "myform_layout.html" too_many_arguments %}')
        with self.assertRaises(TemplateSyntaxError):
            render('{% form myform %}{% endform %}')
        with self.assertRaises(TemplateSyntaxError):
            render('{% form myform using "myform_layout.html" %}{% endform %}')
