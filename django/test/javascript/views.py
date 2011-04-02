from __future__ import with_statement

import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.http import Http404
from django.utils import simplejson
from django.utils.datastructures import SortedDict
from django.utils.importlib import import_module
from django.views import generic, static


class QUnitOverview(generic.TemplateView):
    manifest = 'suite.json'
    template_name = 'qunit/overview.html'

    def __init__(self, *args, **kwargs):
        super(QUnitOverview, self).__init__(*args, **kwargs)
        self.suites = self.get_suites(*args, **kwargs)

    def get_suites(self, **kwargs):
        suites = SortedDict()
        for app_name in settings.INSTALLED_APPS:
            mod = import_module(app_name)
            mod_path = os.path.dirname(mod.__file__)
            label = app_name.split('.')[-1]
            tests_path = os.path.join(mod_path, 'static', label, 'tests')
            if os.path.isfile(os.path.join(tests_path, self.manifest)):
                suites[label] = {
                    "local_urls": [],
                    "remote_urls": [],
                    "name": app_name,
                    "tests_path": tests_path,
                }
        return suites

    def get_context_data(self, **kwargs):
        context = super(QUnitOverview, self).get_context_data(**kwargs)
        context["suites"] = self.suites
        return context


class QUnitRunner(QUnitOverview):
    template_name = 'qunit/runner.html'

    def get(self, request, label=None, path=None, *args, **kwargs):
        """
        
        """
        if label not in self.suites:
            raise Http404("No test suite found with label '%s'" % label)
        suite = self.suites.get(label)
        full_path = os.path.join(suite['tests_path'], path)
        if os.path.isfile(full_path):
            directory, filename = os.path.split(full_path)
            return static.serve(request, path=filename, document_root=directory)
        storage = FileSystemStorage(location=full_path, base_url="")
        context = self.get_context_data(suite, storage, **kwargs)
        return self.render_to_response(context)

    def get_context_data(self, suite, storage, **kwargs):
        context = super(QUnitRunner, self).get_context_data(**kwargs)
        # load suite.json if present
        if storage.exists(self.manifest):
            with storage.open(self.manifest) as json:
                suite.update(simplejson.loads(json.read()))
        directories, files = storage.listdir('.')
        context.update({
            'suite': suite,
            'subsuites': directories,
            'files': [file for file in files if file.endswith('js')],
        })
        return context
