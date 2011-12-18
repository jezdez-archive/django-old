import os
import re
from optparse import make_option
from random import choice

from django.core.management.base import copy_helper, BaseCommand, CommandError
from django.utils.importlib import import_module


class Command(BaseCommand):
    help = ("Creates a Django project directory structure for the given "
            "project name in the current directory or optionally in the "
            "given directory.")
    args = "[projectname] [optional destination directory]"

    option_list = BaseCommand.option_list + (
        make_option('--template',
                    action='store', dest='template', default='django.conf',
                    help='The dotted import path to load the template from.'),
    )

    requires_model_validation = False
    # Can't import settings during this command, because they haven't
    # necessarily been created.
    can_import_settings = False

    def handle(self, project_name=None, directory=None, *args, **options):
        if project_name is None:
            raise CommandError("you must provide a project name")

        # Check that the project_name cannot be imported.
        try:
            import_module(project_name)
        except ImportError:
            pass
        else:
            raise CommandError("%r conflicts with the name of an existing "
                               "Python module and cannot be used as a "
                               "project name. Please try another name." %
                               project_name)

        # Create a random SECRET_KEY hash to put it in the main settings.
        chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
        options['secret_key'] = ''.join([choice(chars) for i in range(50)])
        copy_helper(self.style, 'project', project_name, directory, **options)
