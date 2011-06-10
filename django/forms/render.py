from django.template.loader import render_to_string
from django.utils.safestring import mark_safe


class FormRenderer(object):
    default_template = 'forms/layouts/default.html'

    def render_template(self, template_name, context):
        return render_to_string((
            'forms/layouts/%s/%s' % (self.layout, template_name),
            'forms/layouts/default/%s' % template_name,
        ), context)

    def render_help_text(self, bound_field):
        help_text = bound_field.field.help_text
        help_text = mark_safe(help_text)
        content = self.render_template('help_text.html', {
            'bound_field': bound_field,
            'help_text': help_text,
        })
        return content

    def render_form(self, form, template_name=None):
        if not template_name:
            template_name = self.template_name
        return render_to_string(template_name, {
            'form': form,
        })
