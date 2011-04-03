from django.conf.urls.defaults import url, patterns

from django.test.javascript.views import JavascriptTestRunner, static_path


urlpatterns = patterns('',
    url('^static/(?P<path>.*)$', 'django.views.static.serve', {'document_root': static_path}, name='javascript-static'),
    url('^$', JavascriptTestRunner.as_view(), name='javascript-test-overview'),
    url('^(?P<label>[\w]+)/(?P<path>.*)$', JavascriptTestRunner.as_view(), name='javascript-test-runner'),
)
