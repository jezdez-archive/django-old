from django.conf.urls.defaults import url, patterns

from django.contrib.qunit.views import QUnitOverview, QUnitRunner

urlpatterns = patterns('',
    url('^$', QUnitOverview.as_view(), name='qunit-test-overview'),
    url('^(?P<label>[\w]+)/(?P<path>.*)$', QUnitRunner.as_view(), name='qunit-test-runner'),
)
