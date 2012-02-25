"""
Form Widget classes specific to the Django admin site.
"""

import copy
from django import forms
from django.contrib.admin.templatetags.admin_static import static
from django.core.urlresolvers import reverse, NoReverseMatch
from django.utils.html import escape
from django.utils.text import Truncator
from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe
from django.utils.encoding import force_unicode


class FilteredSelectMultiple(forms.SelectMultiple):
    """
    A SelectMultiple with a JavaScript filter interface.

    Note that the resulting JavaScript assumes that the jsi18n
    catalog has been loaded in the page
    """
    template_name = 'admin/forms/filtered_select_multiple.html'

    @property
    def media(self):
        js = ["core.js", "SelectBox.js", "SelectFilter2.js"]
        return forms.Media(js=[static("admin/js/%s" % path) for path in js])

    def __init__(self, verbose_name, is_stacked, attrs=None, choices=()):
        self.verbose_name = verbose_name
        self.is_stacked = is_stacked
        super(FilteredSelectMultiple, self).__init__(attrs, choices)

    def get_context(self, name, value, attrs, choices, **kwargs):
        if attrs is None:
            attrs = {}
        attrs['class'] = 'selectfilter'
        if self.is_stacked:
            attrs['class'] += 'stacked'
        context = super(FilteredSelectMultiple, self).get_context(
            name, value, attrs=attrs, choices=choices, **kwargs)

        context.update({
            'verbose_name': self.verbose_name.replace('"', '\\"'),
            'is_stacked': int(self.is_stacked),
            'value': map(force_unicode, value),
            'multiple': True,
        })
        return context

class AdminDateWidget(forms.DateInput):

    @property
    def media(self):
        js = ["calendar.js", "admin/DateTimeShortcuts.js"]
        return forms.Media(js=[static("admin/js/%s" % path) for path in js])

    def __init__(self, attrs=None, format=None):
        final_attrs = {'class': 'vDateField', 'size': '10'}
        if attrs is not None:
            final_attrs.update(attrs)
        super(AdminDateWidget, self).__init__(attrs=final_attrs, format=format)

class AdminTimeWidget(forms.TimeInput):

    @property
    def media(self):
        js = ["calendar.js", "admin/DateTimeShortcuts.js"]
        return forms.Media(js=[static("admin/js/%s" % path) for path in js])

    def __init__(self, attrs=None, format=None):
        final_attrs = {'class': 'vTimeField', 'size': '8'}
        if attrs is not None:
            final_attrs.update(attrs)
        super(AdminTimeWidget, self).__init__(attrs=final_attrs, format=format)

class AdminSplitDateTime(forms.SplitDateTimeWidget):
    """
    A SplitDateTime Widget that has some admin-specific styling.
    """
    template_name = 'admin/forms/split_datetime.html'

    def __init__(self, attrs=None):
        widgets = [AdminDateWidget, AdminTimeWidget]
        # Note that we're calling MultiWidget, not SplitDateTimeWidget, because
        # we want to define widgets.
        forms.MultiWidget.__init__(self, widgets, attrs)

    def get_context_data(self):
        return {'date': _('Date:'), 'time': _('Time:')}


class AdminRadioSelect(forms.RadioSelect):
    template_name = 'admin/forms/radio.html'


class AdminFileWidget(forms.ClearableFileInput):
    template_name = 'admin/forms/admin_file.html'


def url_params_from_lookup_dict(lookups):
    """
    Converts the type of lookups specified in a ForeignKey limit_choices_to
    attribute to a dictionary of query parameters
    """
    params = {}
    if lookups and hasattr(lookups, 'items'):
        items = []
        for k, v in lookups.items():
            if isinstance(v, (tuple, list)):
                v = u','.join([str(x) for x in v])
            elif isinstance(v, bool):
                # See django.db.fields.BooleanField.get_prep_lookup
                v = ('0', '1')[v]
            else:
                v = unicode(v)
            items.append((k, v))
        params.update(dict(items))
    return params

class ForeignKeyRawIdWidget(forms.TextInput):
    """
    A Widget for displaying ForeignKeys in the "raw_id" interface rather than
    in a <select> box.
    """
    template_name = 'admin/forms/foreignkey_raw_id.html'

    def __init__(self, rel, admin_site, attrs=None, using=None):
        self.rel = rel
        self.admin_site = admin_site
        self.db = using
        super(ForeignKeyRawIdWidget, self).__init__(attrs)

    def get_context(self, name, value, attrs=None, **kwargs):
        rel_to = self.rel.to
        if attrs is None:
            attrs = {}

        context = super(ForeignKeyRawIdWidget, self).get_context(
            name, value, attrs=attrs, **kwargs)

        if rel_to in self.admin_site._registry:
            # The related object is registered with the same AdminSite
            related_url = reverse('admin:%s_%s_changelist' %
                                    (rel_to._meta.app_label,
                                    rel_to._meta.module_name),
                                    current_app=self.admin_site.name)

            params = self.url_parameters()
            url = u''
            if params:
                url = u'?' + u'&'.join([u'%s=%s' % (k, v) for k, v in params.items()])
            if "class" not in context['attrs']:
                context['attrs']['class'] = 'vForeignKeyRawIdAdminField' # The JavaScript code looks for this hook.

            context.update({
                'related_url': related_url,
                'url': url,
                'alt': _('Lookup'),
            })

        context['label'] = mark_safe(self.label_for_value(value))
        return context

    def base_url_parameters(self):
        return url_params_from_lookup_dict(self.rel.limit_choices_to)

    def url_parameters(self):
        from django.contrib.admin.views.main import TO_FIELD_VAR
        params = self.base_url_parameters()
        params.update({TO_FIELD_VAR: self.rel.get_related_field().name})
        return params

    def label_for_value(self, value):
        key = self.rel.get_related_field().name
        try:
            obj = self.rel.to._default_manager.using(self.db).get(**{key: value})
            return '&nbsp;<strong>%s</strong>' % escape(Truncator(obj).words(14, truncate='...'))
        except (ValueError, self.rel.to.DoesNotExist):
            return ''

class ManyToManyRawIdWidget(ForeignKeyRawIdWidget):
    """
    A Widget for displaying ManyToMany ids in the "raw_id" interface rather than
    in a <select multiple> box.
    """
    template_name = 'admin/forms/foreignkey_raw_id.html'

    def get_context(self, name, value, attrs=None, **kwargs):
        if attrs is None:
            attrs = {}
        if self.rel.to in self.admin_site._registry:
            # The related object is registered with the same AdminSite
            attrs['class'] = 'vManyToManyRawIdAdminField'
        if value:
            value = ','.join([force_unicode(v) for v in value])
        else:
            value = ''
        return super(ManyToManyRawIdWidget, self).get_context(name, value, attrs=attrs, **kwargs)

    def url_parameters(self):
        return self.base_url_parameters()

    def label_for_value(self, value):
        return ''

    def value_from_datadict(self, data, files, name):
        value = data.get(name)
        if value:
            return value.split(',')

    def _has_changed(self, initial, data):
        if initial is None:
            initial = []
        if data is None:
            data = []
        if len(initial) != len(data):
            return True
        for pk1, pk2 in zip(initial, data):
            if force_unicode(pk1) != force_unicode(pk2):
                return True
        return False

class RelatedFieldWidgetWrapper(forms.Widget):
    """
    This class is a wrapper to a given widget to add the add icon for the
    admin interface.
    """
    template_name = 'admin/forms/related_field.html'

    def __init__(self, widget, rel, admin_site, can_add_related=None):
        self.is_hidden = widget.is_hidden
        self.needs_multipart_form = widget.needs_multipart_form
        self.attrs = widget.attrs
        self.choices = widget.choices
        self.widget = widget
        self.rel = rel
        # Backwards compatible check for whether a user can add related
        # objects.
        if can_add_related is None:
            can_add_related = rel.to in admin_site._registry
        self.can_add_related = can_add_related
        # so we can check if the related object is registered with this AdminSite
        self.admin_site = admin_site

    def __deepcopy__(self, memo):
        obj = copy.copy(self)
        obj.widget = copy.deepcopy(self.widget, memo)
        obj.attrs = self.widget.attrs
        memo[id(self)] = obj
        return obj

    @property
    def media(self):
        return self.widget.media

    def get_context(self, name, value, *args, **kwargs):
        rel_to = self.rel.to
        info = (rel_to._meta.app_label, rel_to._meta.object_name.lower())
        self.widget.choices = self.choices
        context = super(RelatedFieldWidgetWrapper, self).get_context(
            name, value, *args, **kwargs)
        if self.can_add_related:
            related_url = reverse('admin:%s_%s_add' % info, current_app=self.admin_site.name)
        else:
            related_url = None
        context.update({
            'widget': self.widget.render(name, value, *args, **kwargs),
            'related_url': related_url,
            'can_add_related': self.can_add_related,
            'name': name,
            'add_another': _('Add Another'),
        })
        return context

    def build_attrs(self, extra_attrs=None, **kwargs):
        "Helper function for building an attribute dictionary."
        self.attrs = self.widget.build_attrs(extra_attrs=None, **kwargs)
        return self.attrs

    def value_from_datadict(self, data, files, name):
        return self.widget.value_from_datadict(data, files, name)

    def _has_changed(self, initial, data):
        return self.widget._has_changed(initial, data)

    def id_for_label(self, id_):
        return self.widget.id_for_label(id_)

class AdminTextareaWidget(forms.Textarea):
    def __init__(self, attrs=None):
        final_attrs = {'class': 'vLargeTextField'}
        if attrs is not None:
            final_attrs.update(attrs)
        super(AdminTextareaWidget, self).__init__(attrs=final_attrs)

class AdminTextInputWidget(forms.TextInput):
    def __init__(self, attrs=None):
        final_attrs = {'class': 'vTextField'}
        if attrs is not None:
            final_attrs.update(attrs)
        super(AdminTextInputWidget, self).__init__(attrs=final_attrs)

class AdminURLFieldWidget(forms.TextInput):
    def __init__(self, attrs=None):
        final_attrs = {'class': 'vURLField'}
        if attrs is not None:
            final_attrs.update(attrs)
        super(AdminURLFieldWidget, self).__init__(attrs=final_attrs)

class AdminIntegerFieldWidget(forms.TextInput):
    def __init__(self, attrs=None):
        final_attrs = {'class': 'vIntegerField'}
        if attrs is not None:
            final_attrs.update(attrs)
        super(AdminIntegerFieldWidget, self).__init__(attrs=final_attrs)

class AdminCommaSeparatedIntegerFieldWidget(forms.TextInput):
    def __init__(self, attrs=None):
        final_attrs = {'class': 'vCommaSeparatedIntegerField'}
        if attrs is not None:
            final_attrs.update(attrs)
        super(AdminCommaSeparatedIntegerFieldWidget, self).__init__(attrs=final_attrs)
