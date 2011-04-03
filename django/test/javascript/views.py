from __future__ import with_statement

import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.http import Http404
from django.utils import simplejson, datastructures
from django.utils.importlib import import_module
from django.views import generic, static
from django.core.urlresolvers import reverse

thisdir = os.path.dirname(__file__)
static_path = os.path.join(thisdir, 'static')
templates_path = os.path.join(thisdir, 'templates')


class JavascriptTestRunner(generic.TemplateView):
    manifest = 'suite.json'
    template_name = 'javascript/runner.html'

    def __init__(self, *args, **kwargs):
        super(JavascriptTestRunner, self).__init__(*args, **kwargs)
        self.suites = datastructures.SortedDict()
        for app_name in settings.INSTALLED_APPS:
            mod = import_module(app_name)
            mod_path = os.path.dirname(mod.__file__)
            label = app_name.split('.')[-1]
            tests_path = os.path.join(mod_path, 'tests', 'javascript')
            if os.path.isdir(tests_path):
                self.suites[label] = {
                    "local_urls": [],
                    "remote_urls": [],
                    "name": app_name,
                    "tests_path": tests_path,
                }

    def get(self, request, label=None, path=None, *args, **kwargs):
        """
        
        """
        if label is not None:
            suite = self.suites.get(label)
            if suite is None:
                raise Http404("No test suite found with label '%s'" % label)
            full_path = os.path.join(suite['tests_path'], path)
            if os.path.isfile(full_path):
                dir, filename = os.path.split(full_path)
                return static.serve(request, path=filename, document_root=dir)
            context = self.get_context_data(suite, full_path, *args, **kwargs)
        else:
            context = self.get_context_data(*args, **kwargs)
        return self.render_to_response(context)

    def get_context_data(self, suite=None, full_path=None, **kwargs):
        context = super(JavascriptTestRunner, self).get_context_data(**kwargs)
        context.update({
            'suites': self.suites,
            'linkbase': reverse('javascript-test-overview'),
        })
        if full_path:
            storage = FileSystemStorage(location=full_path)
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
