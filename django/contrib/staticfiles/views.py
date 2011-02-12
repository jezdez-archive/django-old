"""
Views and functions for serving static files. These are only to be used during
development, and SHOULD NOT be used in a production setting.

"""
import os

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import Http404
from django.views.static import serve as static_serve

from django.contrib.staticfiles import finders

def serve(request, path, document_root=None, insecure=False, **kwargs):
    """
    Serve static files below a given point in the directory structure or
    from locations inferred from the static files finders.

    To use, put a URL pattern such as::

        (r'^(?P<path>.*)$', 'django.contrib.staticfiles.views.serve')

    in your URLconf.

    If you provide the ``document_root`` parameter, the file won't be looked
    up with the staticfiles finders, but in the given filesystem path, e.g.::

    (r'^(?P<path>.*)$', 'django.contrib.staticfiles.views.serve', {'document_root' : '/path/to/my/files/'})

    You may also set ``show_indexes`` to ``True`` if you'd like to serve a
    basic index of the directory.  This index view will use the
    template hardcoded below, but if you'd like to override it, you can create
    a template called ``static/directory_index.html``.
    """
    if not settings.DEBUG and not insecure:
        raise ImproperlyConfigured("The staticfiles view can only be used in "
                                   "debug mode or if the the --insecure "
                                   "option of 'runserver' is used")
    if not document_root:
        path = os.path.normpath(path)
        absolute_path = finders.find(path)
        if not absolute_path:
            raise Http404('"%s" could not be found' % path)
        document_root, path = os.path.split(absolute_path)
    return static_serve(request, path, document_root=document_root, **kwargs)
