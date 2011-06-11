from django.template.base import Library
from django.template.base import Node, NodeList, Template, Context, Variable
from django.template.base import TemplateSyntaxError, VariableDoesNotExist


register = Library()


class FormNode(Node):
    default_template_name = ''

    def __init__(self, tagname, forms, template_name=None, nodelist=None):
        self.tagname = tagname
        self.forms = forms
        self.template_name = template_name
        self.nodelist = nodelist

    def render(self, context):
        return u''

    @classmethod
    def parse(cls, parser, tokens):
        bits = tokens.split_contents()
        tagname = bits.pop(0)
        forms = []
        using = False
        template_name = None
        nodelist = None
        if len(bits) < 1:
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
