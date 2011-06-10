import re

from django.utils.datastructures import SortedDict
from django.utils.importlib import import_module

DEFAULT_NAMES = ('verbose_name', 'db_prefix', 'models_path')

def get_verbose_name(class_name):
    new = re.sub('(((?<=[a-z])[A-Z])|([A-Z](?![A-Z]|$)))', ' \\1', class_name)
    return new.lower().strip()

class AppOptions(object):
    def __init__(self, name, meta):
        self.name = name
        self.meta = meta
        self.errors = []
        self.models = SortedDict()

    def contribute_to_class(self, cls, name):
        cls._meta = self
        # get the name from the path e.g. "auth" for "django.contrib.auth"
        self.label = self.name.split('.')[-1]
        self.models_module = None
        self.module = import_module(self.name)
        defaults = {
            'db_prefix': self.label,
            'models_path': '%s.models' % self.name,
            'verbose_name': get_verbose_name(self.label),
        }
        # Next, apply any overridden values from 'class Meta'.
        if self.meta:
            meta_attrs = self.meta.__dict__.copy()
            for name in self.meta.__dict__:
                # Ignore any private attributes that Django doesn't care about.
                if name.startswith('_'):
                    del meta_attrs[name]
            from django.apps.base import AppBase
            parents = [b for b in cls.__bases__
                       if isinstance(b, AppBase) and hasattr(b, '_meta')]
            for attr_name in DEFAULT_NAMES:
                if attr_name in meta_attrs:
                    setattr(self, attr_name, meta_attrs.pop(attr_name))
                elif hasattr(self.meta, attr_name):
                    setattr(self, attr_name, getattr(self.meta, attr_name))
                else:
                    for parent in parents:
                        if getattr(parent._meta, attr_name) != defaults.get(attr_name):
                            setattr(self, attr_name, getattr(parent._meta, attr_name))
            # Any leftover attributes must be invalid.
            if meta_attrs != {}:
                raise TypeError("'class Meta' got invalid attribute(s): %s"
                                % ','.join(meta_attrs.keys()))
        del self.meta
        for k, v in defaults.iteritems():
            if not hasattr(self, k):
                setattr(self, k, v)
