import os
from optparse import make_option

from django.core.management.base import copy_helper, CommandError, BaseCommand
from django.utils.importlib import import_module


class Command(BaseCommand):
    help = ("Creates a Django app directory structure for the given app "
            "name in the current directory or optionally in the given "
            "directory.")
    args = "[appname] [optional destination directory]"

    option_list = BaseCommand.option_list + (
        make_option('--template',
                    action='store', dest='template', default='django.conf',
                    help='The dotted import path to load the template from.'),
    )

    requires_model_validation = False
    # Can't import settings during this command, because they haven't
    # necessarily been created.
    can_import_settings = False

    def handle(self, app_name=None, directory=None, **options):
        if app_name is None:
            raise CommandError("you must provide an app name")

        # Check that the app_name cannot be imported.
        try:
            import_module(app_name)
        except ImportError:
            pass
        else:
            raise CommandError("%r conflicts with the name of an existing "
                               "Python module and cannot be used as an app "
                               "name. Please try another name." % app_name)

        copy_helper(self.style, 'app', app_name, directory, **options)
