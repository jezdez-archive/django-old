from django.conf.urls.defaults import *
from django.contrib.comments.urls import urlpatterns

urlpatterns += patterns('django.contrib.comments.views',
    url(r'^delete-really/(\d+)/$',  'moderation.delete', {'next': '/deletion/done'}),
)
