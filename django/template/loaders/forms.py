"""
Wrapper for loading the default forms templates, located in
django/forms/templates.
"""

import os

from django import forms
from django.conf import settings
from django.template.base import TemplateDoesNotExist
from django.template.base import BaseLoader
from django.template.loaders.cached import Loader as CachedLoader
from django.utils._os import safe_join


class FormsLoader(BaseLoader):
    is_usable = True
    _auto_added = False  # whether the loader has been automatically enabled

    def load_template_source(self, template_name, template_dirs=None):
        forms_template_dir = os.path.join(os.path.dirname(forms.__file__),
                                          'templates')
        template_path = safe_join(forms_template_dir, template_name)

        try:
            template_file = open(template_path)
            try:
                content = template_file.read().decode(settings.FILE_CHARSET)
                if self._auto_added:
                    import warnings
                    warnings.warn(("The forms template loader has been "
                                   "automatically enabled, you need to add it "
                                   "to your TEMPLATE_LOADERS."),
                                  PendingDeprecationWarning)
                return (content, template_path)
            finally:
                template_file.close()
        except IOError:
            pass
        raise TemplateDoesNotExist(template_name)


class Loader(CachedLoader):

    def __init__(self):
        real_loader = 'django.template.loaders.forms.FormsLoader'
        super(Loader, self).__init__([real_loader])
