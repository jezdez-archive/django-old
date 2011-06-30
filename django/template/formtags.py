from django.conf import settings
from django.template.base import Library
from django.template.base import Node, Variable
from django.template.base import TemplateSyntaxError, VariableDoesNotExist
from django.template.defaulttags import token_kwargs
from django.template.loader import get_template


register = Library()


class BaseFormAndRowNode(Node):
    default_template_name = None
    single_template_var = None
    list_template_var = None

    def __init__(self, tagname, variables, options):
        self.tagname = tagname
        self.variables = variables
        self.options = options

    def render(self, context):
        if 'nodelist' not in self.options:
            try:
                if 'template_name' in self.options:
                    template_name = self.options['template_name'].resolve(context)
                else:
                    template_name = self.default_template_name
                nodelist = get_template(template_name)
            except:
                if settings.TEMPLATE_DEBUG:
                    raise
                return u''
        else:
            nodelist = self.options['nodelist']
        variables = []
        for variable in self.variables:
            try:
                variable = variable.resolve(context)
                variables.append(variable)
            except VariableDoesNotExist:
                pass

        extra_context = {
            self.single_template_var: variables[0] if variables else None,
            self.list_template_var: variables,
        }

        if self.options['with']:
            extra_context.update(dict([
                (name, var.resolve(context))
                for name, var in self.options['with'].iteritems()]))

        if self.options['only']:
            context = context.new(extra_context)
            return nodelist.render(context)

        context.update(extra_context)
        output = nodelist.render(context)
        context.pop()
        return output

    @classmethod
    def parse_variables(cls, tagname, parser, bits, options):
        variables = []
        while bits and bits[0] not in ('using', 'with', 'only'):
            variables.append(Variable(bits.pop(0)))
        if not variables:
            raise TemplateSyntaxError(
                u'%s tag expectes at least one template variable as argument.' % tagname)
        return variables

    @classmethod
    def parse_using(cls, tagname, parser, bits, options):
        raise NotImplementedError(u'Must be implemented in subclass')

    @classmethod
    def parse_with(cls, tagname, parser, bits, options):
        if bits:
            if bits[0] == 'with':
                bits.pop(0)
                arguments = token_kwargs(bits, parser, support_legacy=False)
                if not arguments:
                    raise TemplateSyntaxError(
                        u'"with" in %s tag needs at least one '
                        u'keyword argument.' % tagname)
                options['with'] = arguments
            elif bits[0] not in ('only',):
                raise TemplateSyntaxError('Unknown argument for %s tag: %r.' %
                    (tagname, bits[0]))

        if bits:
            if bits[0] == 'only':
                bits.pop(0)
                options['only'] = True

    @classmethod
    def parse(cls, parser, tokens):
        bits = tokens.split_contents()
        tagname = bits.pop(0)
        options = {
            'only': False,
            'with': None,
        }

        variables = cls.parse_variables(tagname, parser, bits, options)
        cls.parse_using(tagname, parser, bits, options)
        cls.parse_with(tagname, parser, bits, options)

        if bits:
            raise TemplateSyntaxError('Unknown argument for %s tag: %r.' %
                (tagname, ' '.join(bits)))

        return cls(tagname, variables, options)


class FormNode(BaseFormAndRowNode):
    default_template_name = 'forms/layouts/default.html'
    single_template_var = 'form'
    list_template_var = 'forms'

    @classmethod
    def parse_using(cls, tagname, parser, bits, options):
        if bits:
            if bits[0] == 'using':
                bits.pop(0)
                if len(bits):
                    if bits[0] in ('with', 'only'):
                        raise TemplateSyntaxError(
                            u'%s: you must provide one template after "using" '
                            u'and before "with" or "only".')
                    options['template_name'] = Variable(bits.pop(0))
                else:
                    nodelist = parser.parse(('end%s' % tagname,))
                    parser.delete_first_token()
                    options['nodelist'] = nodelist
            else:
                raise TemplateSyntaxError('Unknown argument for %s tag: %r.' %
                    (tagname, bits[0]))


class FormRowNode(BaseFormAndRowNode):
    default_template_name = 'forms/rows/default.html'
    single_template_var = 'field'
    list_template_var = 'fields'

    @classmethod
    def parse_using(cls, tagname, parser, bits, options):
        if bits:
            if bits[0] == 'using':
                bits.pop(0)
                if len(bits):
                    if bits[0] in ('with', 'only'):
                        raise TemplateSyntaxError(
                            u'%s: you must provide one template after "using" '
                            u'and before "with" or "only".')
                    options['template_name'] = Variable(bits.pop(0))
                else:
                    raise TemplateSyntaxError(
                        u'%s: expected a template name after "using".' % tagname)
            else:
                raise TemplateSyntaxError('Unknown argument for %s tag: %r.' %
                    (tagname, bits[0]))


register.tag('form', FormNode.parse)
register.tag('formrow', FormRowNode.parse)
