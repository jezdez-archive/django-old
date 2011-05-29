"""
Form Widget classes specific to the Django admin site.
"""

import copy
from django import forms
from django.forms.widgets import RadioFieldRenderer
from django.forms.util import flatatt
from django.utils.html import escape
from django.utils.text import truncate_words
from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe
from django.utils.encoding import force_unicode
from django.conf import settings
from django.core.urlresolvers import reverse, NoReverseMatch


class FilteredSelectMultiple(forms.SelectMultiple):
    """
    A SelectMultiple with a JavaScript filter interface.

    Note that the resulting JavaScript assumes that the jsi18n
    catalog has been loaded in the page
    """
    template_name = 'admin/forms/filtered_select_multiple.html'

    class Media:
        js = (settings.ADMIN_MEDIA_PREFIX + "js/core.js",
              settings.ADMIN_MEDIA_PREFIX + "js/SelectBox.js",
              settings.ADMIN_MEDIA_PREFIX + "js/SelectFilter2.js")

    def __init__(self, verbose_name, is_stacked, attrs=None, choices=()):
        self.verbose_name = verbose_name
        self.is_stacked = is_stacked
        super(FilteredSelectMultiple, self).__init__(attrs, choices)

    def get_context(self, name, value, attrs, choices):
        attrs = attrs or {}
        attrs['class'] = 'selectfilter'
        if self.is_stacked:
            attrs['class'] += 'stacked'
        context = super(FilteredSelectMultiple,
                        self).get_context(name, value, attrs, choices)

        context.update({
            'verbose_name': self.verbose_name.replace('"', '\\"'),
            'is_stacked': int(self.is_stacked),
            'prefix': settings.ADMIN_MEDIA_PREFIX,
            'value': map(force_unicode, value),
            'multiple': True,
        })
        return context


class AdminDateWidget(forms.DateInput):
    class Media:
        js = (settings.ADMIN_MEDIA_PREFIX + "js/calendar.js",
              settings.ADMIN_MEDIA_PREFIX + "js/admin/DateTimeShortcuts.js")

    def __init__(self, attrs={}, format=None):
        super(AdminDateWidget, self).__init__(attrs={'class': 'vDateField', 'size': '10'}, format=format)

class AdminTimeWidget(forms.TimeInput):
    class Media:
        js = (settings.ADMIN_MEDIA_PREFIX + "js/calendar.js",
              settings.ADMIN_MEDIA_PREFIX + "js/admin/DateTimeShortcuts.js")

    def __init__(self, attrs={}, format=None):
        super(AdminTimeWidget, self).__init__(attrs={'class': 'vTimeField', 'size': '8'}, format=format)

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

    def __init__(self, rel, attrs=None, using=None):
        self.rel = rel
        self.db = using
        super(ForeignKeyRawIdWidget, self).__init__(attrs)

    def get_context(self, name, value, attrs=None):
        attrs = attrs or {}
        if "class" not in attrs:
            # The JavaScript looks for this hook.
            attrs['class'] = 'vForeignKeyRawIdAdminField'

        context = super(ForeignKeyRawIdWidget,
                        self).get_context(name, value, attrs)

        context['related_url'] = '../../../%s/%s/' % (
            self.rel.to._meta.app_label, self.rel.to._meta.object_name.lower())

        params = self.url_parameters()
        url = u''
        if params:
            url = u'?' + u'&'.join([u'%s=%s' % (k, v) for k, v in params.items()])
        context.update({
            'url': url,
            'alt': _('Lookup'),
            'admin_media_prefix': settings.ADMIN_MEDIA_PREFIX,
            'label': mark_safe(self.label_for_value(value)),
        })
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
            return '&nbsp;<strong>%s</strong>' % escape(truncate_words(obj, 14))
        except (ValueError, self.rel.to.DoesNotExist):
            return ''

class ManyToManyRawIdWidget(ForeignKeyRawIdWidget):
    """
    A Widget for displaying ManyToMany ids in the "raw_id" interface rather than
    in a <select multiple> box.
    """
    template_name = 'admin/forms/foreignkey_raw_id.html'

    def get_context(self, name, value, attrs=None):
        attrs = attrs or {}
        if "class" not in attrs:
            # The JavaScript looks for this hook.
            attrs['class'] = 'vManyToManyRawIdAdminField'

        if value:
            value = ','.join([force_unicode(v) for v in value])
        else:
            value = ''

        return super(ManyToManyRawIdWidget,
                     self).get_context(name, value, attrs)

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

    def _media(self):
        return self.widget.media
    media = property(_media)

    def get_context(self, name, value, *args, **kwargs):
        rel_to = self.rel.to
        info = (rel_to._meta.app_label, rel_to._meta.object_name.lower())
        try:
            related_url = reverse('admin:%s_%s_add' % info, current_app=self.admin_site.name)
        except NoReverseMatch:
            info = (self.admin_site.root_path, rel_to._meta.app_label, rel_to._meta.object_name.lower())
            related_url = '%s%s/%s/add/' % info
        self.widget.choices = self.choices
        output = [self.widget.render(name, value, *args, **kwargs)]
        ctx = super(RelatedFieldWidgetWrapper,
                    self).get_context(name, value, *args, **kwargs)
        ctx.update({
            'widget': self.widget.render(name, value, *args, **kwargs),
            'related_url': related_url,
            'can_add_related': self.can_add_related,
            'name': name,
            'ADMIN_MEDIA_PREFIX': settings.ADMIN_MEDIA_PREFIX,
            'add_another': _('Add Another'),
        })
        return ctx

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
