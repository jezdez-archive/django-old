from optparse import make_option

from django.conf import settings
from django.core.handlers.wsgi import WSGIHandler
from django.core.management.commands.runserver import BaseRunserverCommand
from django.http import Http404
from django.views import debug

from django.test.javascript.views import templates_path


class JavascriptTestHandler(WSGIHandler):

    def get_response(self, request):
        request.urlconf = "django.test.javascript.urls"
        return super(JavascriptTestHandler, self).get_response(request)


class Command(BaseRunserverCommand):
    help = 'Runs the Javascript test runner'

    def get_handler(self, *args, **options):
        settings.TEMPLATE_DIRS = list(settings.TEMPLATE_DIRS) + [templates_path]
        return JavascriptTestHandler(*args)
