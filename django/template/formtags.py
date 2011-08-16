from collections import defaultdict
from django.conf import settings
from django.template.base import Library
from django.template.base import Node, Variable
from django.template.base import TemplateSyntaxError, VariableDoesNotExist
from django.template.defaulttags import token_kwargs
from django.template.loader import get_template


register = Library()


class ConfigFilter(object):
    '''
    Can be used as ``filter`` argument to ``FormConfig.configure()``. This
    filter matches to a bound field based on three criterias:

    It will return ``True`` if:

    * the bound field passed into the constructor equals the filtered field.
    * the string passed into the constructor equals the fields name.
    * the string passed into the constructor equals the field's class name.
    '''
    def __init__(self, var):
        self.var = var

    def __call__(self, bound_field):
        # when var is a bound_field ...
        # bound fields cannot be compared since form['field'] returns a new
        # instance every time it's called
        if hasattr(self.var, 'form') and hasattr(self.var, 'name'):
            if self.var.form is bound_field.form:
                if self.var.name == bound_field.name:
                    return True
        if self.var == bound_field.name:
            return True
        for class_ in bound_field.field.__class__.__mro__:
            if self.var == class_.__name__:
                return True

    def __repr__(self):
        return "<%s: %r>" % (self.__class__.__name__, self.var)


def default_label(bound_field, **kwargs):
    if bound_field:
        return bound_field.label


def default_help_text(bound_field, **kwargs):
    if bound_field:
        return bound_field.field.help_text


def default_widget(bound_field, **kwargs):
    if bound_field:
        return bound_field.field.widget


def default_widget_template(bound_field, **kwargs):
    if bound_field:
        return bound_field.field.widget.template_name


class ConfigPopException(Exception):
    "pop() has been called more times than push()"
    pass


class FormConfig(object):
    defaults = {
        'layout': lambda **kwargs: 'forms/layouts/default.html',
        'row_template': lambda **kwargs: 'forms/rows/default.html',
        'label': default_label,
        'help_text': default_help_text,
        'widget': default_widget,
        'widget_template': default_widget_template,
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

    def retrieve_all(self, key, **kwargs):
        '''
        Returns a list of found values for ``key``, ordered by
        most-recently-configured.
        '''
        values = []
        for d in self.dicts:
            for value, filter in d[key]:
                if filter(**kwargs):
                    values.insert(0, value)
        return values


class BaseNode(Node):
    CONFIG_CONTEXT_ATTR = '_form_config'
    IN_FORM_CONTEXT_VAR = '_form_render'

    form_config = FormConfig
    single_template_var = None
    list_template_var = None

    def __init__(self, tagname, variables, options):
        self.tagname = tagname
        self.variables = variables
        self.options = options

    def get_config(self, context):
        try:
            return getattr(context, self.CONFIG_CONTEXT_ATTR)
        except AttributeError:
            config = self.form_config()
            setattr(context, self.CONFIG_CONTEXT_ATTR, config)
            return config

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
    def parse_using(cls, tagname, parser, bits, options, optional=False):
        if bits:
            if bits[0] == 'using':
                bits.pop(0)
                if len(bits):
                    if bits[0] in ('with', 'only'):
                        raise TemplateSyntaxError(
                            u'%s: you must provide one template after "using" '
                            u'and before "with" or "only".')
                    options['using'] = Variable(bits.pop(0))
                else:
                    raise TemplateSyntaxError(
                        u'%s: expected a template name after "using".' % tagname)
            elif not optional:
                raise TemplateSyntaxError('Unknown argument for %s tag: %r.' %
                    (tagname, bits[0]))

    @classmethod
    def parse_with(cls, tagname, parser, bits, options, allow_only=True, optional=False):
        if bits:
            if bits[0] == 'with':
                bits.pop(0)
                arguments = token_kwargs(bits, parser, support_legacy=False)
                if not arguments:
                    raise TemplateSyntaxError(
                        u'"with" in %s tag needs at least one '
                        u'keyword argument.' % tagname)
                options['with'] = arguments
            elif bits[0] not in ('only',) and not optional:
                raise TemplateSyntaxError('Unknown argument for %s tag: %r.' %
                    (tagname, bits[0]))

        if bits:
            if allow_only and bits[0] == 'only':
                bits.pop(0)
                options['only'] = True

    @classmethod
    def parse_for(cls, tagname, parser, bits, options, optional=False):
        if bits:
            if bits[0] == 'for':
                bits.pop(0)
                if len(bits):
                    options['for'] = Variable(bits.pop(0))
                else:
                    raise TemplateSyntaxError(
                        u'%s: expected an argument after "for".' % tagname)
            elif not optional:
                raise TemplateSyntaxError('Unknown argument for %s tag: %r.' %
                    (tagname, bits[0]))

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


class ModifierBase(BaseNode):
    def __init__(self, tagname, modifier, options):
        self.tagname = tagname
        self.modifer = modifier
        self.options = options

    def enforce_form_tag(self, context):
        if not context.get(self.IN_FORM_CONTEXT_VAR, False):
            raise TemplateSyntaxError(
                u'%s must be used inside a form tag.' % self.tagname)

    def render(self, context):
        self.enforce_form_tag(context)
        return u''


class RowModifier(ModifierBase):
    def render(self, context):
        self.enforce_form_tag(context)
        config = self.get_config(context)
        if self.options['using']:
            try:
                template_name = self.options['using'].resolve(context)
            except VariableDoesNotExist:
                if settings.TEMPLATE_DEBUG:
                    raise
                return u''
            config.configure('row_template', template_name)
        if self.options['with']:
            extra_context = dict([
                (name, var.resolve(context))
                for name, var in self.options['with'].iteritems()])
            config.configure('row_context', extra_context)
        return u''

    @classmethod
    def parse_bits(cls, tagname, modifier, bits, parser, tokens):
        options = {
            'using': None,
            'with': None,
        }

        if not bits:
            raise TemplateSyntaxError('%s %s: at least one argument is required.' %
                (tagname, modifier))

        cls.parse_using(tagname, parser, bits, options, optional=True)
        cls.parse_with(tagname, parser, bits, options, allow_only=False, optional=True)

        if bits:
            raise TemplateSyntaxError('Unknown argument for %s %s tag: %r.' %
                (tagname, modifier, ' '.join(bits)))

        return cls(tagname, modifier, options)


class FieldModifier(ModifierBase):
    def render(self, context):
        self.enforce_form_tag(context)
        config = self.get_config(context)
        filter = None
        if self.options['for']:
            try:
                var = self.options['for'].resolve(context)
            except VariableDoesNotExist:
                if settings.TEMPLATE_DEBUG:
                    raise
                return ''
            filter = ConfigFilter(var)
        if self.options['using']:
            try:
                template_name = self.options['using'].resolve(context)
            except VariableDoesNotExist:
                if settings.TEMPLATE_DEBUG:
                    raise
                return ''
            config.configure('widget_template', template_name, filter=filter)
        if self.options['with']:
            extra_context = dict([
                (name, var.resolve(context))
                for name, var in self.options['with'].iteritems()])
            config.configure('widget_context', extra_context, filter=filter)
        return ''

    @classmethod
    def parse_bits(cls, tagname, modifier, bits, parser, tokens):
        options = {
            'using': None,
            'with': None,
            'for': None,
        }

        if not bits:
            raise TemplateSyntaxError('%s %s: at least one argument is required.' %
                (tagname, modifier))

        cls.parse_using(tagname, parser, bits, options, optional=True)
        cls.parse_with(tagname, parser, bits, options, allow_only=False, optional=True)
        cls.parse_for(tagname, parser, bits, options, optional=True)

        if bits:
            raise TemplateSyntaxError('Unknown argument for %s %s tag: %r.' %
                (tagname, modifier, ' '.join(bits)))

        return cls(tagname, modifier, options)


class FormConfigNode(BaseNode):
    MODIFIERS = {
        'row': RowModifier,
        'field': FieldModifier,
    }

    @classmethod
    def parse(cls, parser, tokens):
        bits = tokens.split_contents()
        tagname = bits.pop(0)
        if not bits or bits[0] not in cls.MODIFIERS:
            raise TemplateSyntaxError(
                '%s needs one of the following keywords as first argument: '
                '%s' % (tagname, ', '.join(cls.MODIFIERS.keys())))
        modifier = bits.pop(0)
        modifier_class = cls.MODIFIERS[modifier]
        return modifier_class.parse_bits(tagname, modifier, bits, parser, tokens)


class BaseFormRenderNode(BaseNode):
    '''
    Base class for ``form``, ``formrow`` and ``formfield`` -- tags that are
    responsible for actually rendering a form.
    '''
    def get_template_name(self, context):
        raise NotImplementedError

    def get_nodelist(self, context, extra_context):
        if 'nodelist' in self.options:
            return self.options['nodelist']
        try:
            if 'using' in self.options:
                template_name = self.options['using'].resolve(context)
            else:
                template_name = self.get_template_name(context)
            return get_template(template_name)
        except:
            if settings.TEMPLATE_DEBUG:
                raise

    def get_extra_context(self, context):
        variables = []
        for variable in self.variables:
            try:
                variable = variable.resolve(context)
                variables.append(variable)
            except VariableDoesNotExist:
                pass

        extra_context =  {
            self.single_template_var: variables[0] if variables else None,
        }
        if self.list_template_var:
            extra_context[self.list_template_var] = variables

        if self.options['with']:
            extra_context.update(dict([
                (name, var.resolve(context))
                for name, var in self.options['with'].iteritems()]))

        return extra_context

    def render(self, context):
        only = self.options['only']

        extra_context = self.get_extra_context(context)
        nodelist = self.get_nodelist(context, extra_context)
        if nodelist is None:
            return ''

        if only:
            context = context.new(extra_context)
            return nodelist.render(context)
        else:
            context.update(extra_context)
            output = nodelist.render(context)
            context.pop()
            return output


class FormNode(BaseFormRenderNode):
    single_template_var = 'form'
    list_template_var = 'forms'

    def get_template_name(self, context):
        config = self.get_config(context)
        return config.retrieve('layout')

    def render(self, context):
        context.push()
        try:
            context[self.IN_FORM_CONTEXT_VAR] = True
            return super(FormNode, self).render(context)
        finally:
            context.pop()

    @classmethod
    def parse_using(cls, tagname, parser, bits, options):
        '''
        Parses content until ``{% endform %}`` if no template name is
        specified after "using".
        '''
        if bits:
            if bits[0] == 'using':
                bits.pop(0)
                if len(bits):
                    if bits[0] in ('with', 'only'):
                        raise TemplateSyntaxError(
                            u'%s: you must provide one template after "using" '
                            u'and before "with" or "only".')
                    options['using'] = Variable(bits.pop(0))
                else:
                    nodelist = parser.parse(('end%s' % tagname,))
                    parser.delete_first_token()
                    options['nodelist'] = nodelist
            else:
                raise TemplateSyntaxError('Unknown argument for %s tag: %r.' %
                    (tagname, bits[0]))


class FormRowNode(BaseFormRenderNode):
    single_template_var = 'field'
    list_template_var = 'fields'

    def get_template_name(self, context):
        config = self.get_config(context)
        return config.retrieve('row_template')

    def get_extra_context(self, context):
        extra_context = super(FormRowNode, self).get_extra_context(context)
        config = self.get_config(context)
        configured_context = {}
        # most recently used values should overwrite older ones
        for extra in reversed(config.retrieve_all('row_context')):
            configured_context.update(extra)
        configured_context.update(extra_context)
        return configured_context

    @classmethod
    def parse_using(cls, tagname, parser, bits, options, optional=True):
        return super(FormRowNode, cls).parse_using(
            tagname, parser, bits, options, optional)


class FormFieldNode(BaseFormRenderNode):
    single_template_var = 'field'

    def get_extra_context(self, context):
        extra_context = super(FormFieldNode, self).get_extra_context(context)
        field = extra_context[self.single_template_var]
        config = self.get_config(context)
        configured_context = {}
        # most recently used values should overwrite older ones
        for extra in reversed(config.retrieve_all('widget_context', bound_field=field)):
            configured_context.update(extra)
        configured_context.update(extra_context)
        return configured_context

    def render(self, context):
        config = self.get_config(context)

        assert len(self.variables) == 1
        try:
            bound_field = self.variables[0].resolve(context)
        except VariableDoesNotExist:
            if settings.DEBUG:
                raise
            return u''

        widget = config.retrieve('widget', bound_field=bound_field)
        extra_context = self.get_extra_context(context)
        template_name = config.retrieve('widget_template', bound_field=bound_field)
        if 'using' in self.options:
            try:
                template_name = self.options['using'].resolve(context)
            except VariableDoesNotExist:
                if settings.DEBUG:
                    raise
                return u''

        if self.options['only']:
            context_instance = context.new(extra_context)
        else:
            context.update(extra_context)
            context_instance = context

        output = bound_field.as_widget(
            widget=widget,
            template_name=template_name,
            context_instance=context_instance)

        if not self.options['only']:
            context.pop()

        if bound_field.field.show_hidden_initial:
            return output + bound_field.as_hidden(only_initial=True)
        return output

    @classmethod
    def parse_variables(cls, tagname, parser, bits, options):
        variables = []
        while bits and bits[0] not in ('using', 'with', 'only'):
            variables.append(Variable(bits.pop(0)))
        if len(variables) != 1:
            raise TemplateSyntaxError(
                u'%s tag expectes exactly one template variable as argument.' % tagname)
        return variables

    @classmethod
    def parse_using(cls, tagname, parser, bits, options, optional=True):
        return super(FormFieldNode, cls).parse_using(
            tagname, parser, bits, options, optional)


register.tag('formconfig', FormConfigNode.parse)
register.tag('form', FormNode.parse)
register.tag('formrow', FormRowNode.parse)
register.tag('formfield', FormFieldNode.parse)
