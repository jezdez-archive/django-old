from django.conf.urls.defaults import patterns
from django.core.urlresolvers import LocaleRegexURLResolver

def i18n_patterns(prefix, *args):
    """
    This will add the language-code prefix to every URLPattern within this
    function. It is only allowed to use this at rootlevel of your URLConf.
    """
    pattern_list = patterns(prefix, *args)
    return [LocaleRegexURLResolver(pattern_list)]


urlpatterns = patterns('',
    (r'^setlang/$', 'django.views.i18n.set_language'),
)
