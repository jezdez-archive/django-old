# Taken from Python 2.7 with permission from/by the original author.
import sys

def _resolve_name(name, package, level):
    """Return the absolute name of the module to be imported."""
    if not hasattr(package, 'rindex'):
        raise ValueError("'package' not set to a string")
    dot = len(package)
    for x in xrange(level, 1, -1):
        try:
            dot = package.rindex('.', 0, dot)
        except ValueError:
            raise ValueError("attempted relative import beyond top-level "
                              "package")
    return "%s.%s" % (package[:dot], name)


def import_module(name, package=None):
    """Import a module.

    The 'package' argument is required when performing a relative import. It
    specifies the package to use as the anchor point from which to resolve the
    relative import to an absolute import.

    """
    if name.startswith('.'):
        if not package:
            raise TypeError("relative imports require the 'package' argument")
        level = 0
        for character in name:
            if character != '.':
                break
            level += 1
        name = _resolve_name(name[level:], package, level)
    __import__(name)
    return sys.modules[name]


def import_attribute(name, exception_handler=None):
    """
    Loads an object from an 'name', like in MIDDLEWARE_CLASSES and the likes.

    Import paths should be: "mypackage.mymodule.MyObject". It then imports the
    module up until the last dot and tries to get the attribute after that dot
    from the imported module.

    If the import path does not contain any dots, a TypeError is raised.

    If the module cannot be imported, an ImportError is raised.

    If the attribute does not exist in the module, a AttributeError is raised.

    You can provide custom error handling using the optional exception_handler
    argument which gets called with the exception type, the exception value and
    the traceback object if there is an error during loading.

    The exception_handler is not called if an invalid import path (one without
    a dot in it) is provided.
    """
    if '.' not in name:
        raise TypeError("'name' argument to "
                        "'django.utils.importlib.import_attribute' must "
                        "contain at least one dot.")
    module_name, object_name = name.rsplit('.', 1)
    try:
        module = import_module(module_name)
    except:
        if callable(exception_handler):
            exctype, excvalue, tb = sys.exc_info()
            return exception_handler(name, exctype, excvalue, tb)
        else:
            raise
    try: 
        return getattr(module, object_name)
    except:
        if callable(exception_handler):
            exctype, excvalue, tb = sys.exc_info()
            return exception_handler(name, exctype, excvalue, tb)
        else:
            raise


def iter_import_attributes(names, exception_handler=None):
    """
    Calls django.contrib.load.import_attribute on all items in the iterable
    names and returns a generator that yields the objects to be loaded.

    The exception_handler is propagated to import_attribute.

    If the exception_handler does not return anything or returns None, the
    value is ignored.
    """
    for name in names:
        next = import_attribute(name, exception_handler)
        if next:
            yield next
