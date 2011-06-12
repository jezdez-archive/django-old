from django.conf import settings
from django.template.base import Library
from django.template.base import Node, Variable
from django.template.base import TemplateSyntaxError, VariableDoesNotExist
from django.template.loader import get_template


register = Library()


class FormNode(Node):
    default_template_name = ''

    def __init__(self, tagname, forms, template_name=None, nodelist=None):
        self.tagname = tagname
        self.forms = forms
        self.template_name = template_name
        self.nodelist = nodelist

    def render(self, context):
        if not self.nodelist:
            try:
                if self.template_name is not None:
                    template_name = self.template_name.resolve(context)
                else:
                    template_name = self.default_template_name
                nodelist = get_template(template_name)
            except:
                if settings.TEMPLATE_DEBUG:
                    raise
                return u''
        else:
            nodelist = self.nodelist
        forms = []
        for variable in self.forms:
            try:
                form = variable.resolve(context)
                forms.append(form)
            except VariableDoesNotExist:
                pass
        context.push()
        try:
            context['form'] = forms[0] if forms else None
            context['forms'] = forms
            return nodelist.render(context)
        finally:
            context.pop()
        return u''

    @classmethod
    def parse(cls, parser, tokens):
        bits = tokens.split_contents()
        tagname = bits.pop(0)
        forms = []
        using = False
        template_name = None
        nodelist = None
        if len(bits) < 1 or bits == ['using']:
            raise TemplateSyntaxError(
                u'%s tag: expected at least one argument' % tagname)
        while bits:
            keyword = bits.pop(0)
            if keyword == 'using':
                using = True
                break
            forms.append(Variable(keyword))
        if using:
            if len(bits) > 1:
                raise TemplateSyntaxError(
                    u'%s tag: more than one argument after '
                    u'"using" specified' % tagname)
            elif len(bits) == 1:
                template_name = Variable(bits.pop(0))
            else:
                nodelist = parser.parse(('end%s' % tagname,))
                parser.delete_first_token()
        return cls(tagname, forms, template_name, nodelist)


register.tag('form', FormNode.parse)
