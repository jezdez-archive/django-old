from collections import defaultdict
from django.conf import settings
from django.template.base import Library
from django.template.base import Node, Variable
from django.template.base import TemplateSyntaxError, VariableDoesNotExist
from django.template.defaulttags import token_kwargs
from django.template.loader import get_template


register = Library()


class Fieldname(object):
    def __init__(self, name):
        self.name = name

    def __call__(self, bound_field):
        if bound_field:
            return bound_field.name == self.name


class Fieldtype(object):
    def __init__(self, field_class):
        self.field_class = field_class

    def __call__(self, bound_field):
        if bound_field:
            return isinstance(bound_field.field, self.field_class)



def default_label(bound_field, **kwargs):
    if bound_field:
        return bound_field.label


def default_help_text(bound_field, **kwargs):
    if bound_field:
        return bound_field.field.help_text


def default_widget(bound_field, **kwargs):
    if bound_field:
        return bound_field.field.widget


class ConfigPopException(Exception):
    "pop() has been called more times than push()"
    pass


class FormConfig(object):
    defaults = {
        'layout': lambda **kwargs: 'forms/layouts/default.html',
        'rowtemplate': lambda **kwargs: 'forms/rows/default.html',
        'label': default_label,
        'help_text': default_help_text,
        'widget': default_widget,
    }

    def __init__(self):
        self.dicts = [self._dict()]

    def _dict(self):
        return defaultdict(lambda: [])

    def push(self):
        d = self._dict()
        self.dicts.append(d)
        return d

    def pop(self):
        if len(self.dicts) == 1:
            raise ConfigPopException
        return self.dicts.pop()

    def configure(self, key, value, filter=None):
        '''
        key: Key under which ``value`` can be retrieved.
        value: value that is returned if retrieve is called with the same key
        '''
        if filter is None:
            filter = lambda **kwargs: True
        self.dicts[-1][key].append((value, filter))

    def retrieve(self, key, **kwargs):
        '''
        key: Key to lookup in key-value store
        **kwargs: A dictionary of kwargs that will be passed into the filters
        of all found values. So the latest added value for key will be
        retrieved. If the value has a ``filter`` attached, then ``filter``
        will be called with ``kwargs``. Value will be returned if ``filter``
        returned ``True``. Otherwise the next available value will be looked
        up.

        If no value is found: return ``self.defaults[key](**kwargs)``
        '''
        for d in reversed(self.dicts):
            for value, filter in reversed(d[key]):
                if filter(**kwargs):
                    return value

        if key not in self.defaults:
            return None
        return self.defaults[key](**kwargs)


class BaseFormAndRowNode(Node):
    CONFIG_CONTEXT_VAR = '_form_config'
    default_template_name = None
    single_template_var = None
    list_template_var = None

    def __init__(self, tagname, variables, options):
        self.tagname = tagname
        self.variables = variables
        self.options = options

    def get_config(self, context):
        try:
            return context[self.CONFIG_CONTEXT_VAR]
        except KeyError:
            config = FormConfig()
            context[self.CONFIG_CONTEXT_VAR]
            return config

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


class FormFieldNode(Node):
    def __init__(self, field):
        self.field = field

    def render(self, context):
        try:
            field = self.field.resolve(context)
        except VariableDoesNotExist:
            if settings.DEBUG:
                raise
            return u''
        return unicode(field)

    @classmethod
    def parse(cls, parser, tokens):
        bits = tokens.split_contents()
        tagname = bits.pop(0)
        if len(bits) != 1:
            raise TemplateSyntaxError('%s expects exactly one argument.' %
                tagname)
        field_var = Variable(bits[0])
        return cls(field_var)


register.tag('form', FormNode.parse)
register.tag('formrow', FormRowNode.parse)
register.tag('formfield', FormFieldNode.parse)
