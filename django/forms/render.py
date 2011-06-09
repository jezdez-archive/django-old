from django.template.loader import render_to_string
from django.utils.safestring import mark_safe


class FormRenderer(object):
    def __init__(self, layout):
        self.layout = layout

    def get_template_paths(self, template_name):
        template_paths = []
        if self.layout:
            template_paths.append('forms/layouts/%s/%s' % (self.layout, template_name))
        template_paths.append('forms/layouts/default/%s' % template_name)
        return template_paths

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
