from django.conf.urls.defaults import *

urlpatterns = patterns('mlmadmin.views',
    url(r'^$', view='main', name='main_current'),
    url(r'^help', view='help', name='help'),
    url(r'^redirect', view='redirect', name='redirect'),
    url(r'^signout', view='signout', name='signout'),
    url(r'^(?P<object_id>.*)/add', view='add', name='add'),
    url(r'^(?P<object_id>.*)/bounce$', view='bounce', name='bounce'),
    url(r'^(?P<object_id>.*)/bulk_search', view='bulk_search', name='bulk_search'),
    url(r'^(?P<object_id>.*)/compose', view='compose', name='compose'),
    url(r'^(?P<object_id>.*)/dump', view='dump', name='dump'),
    url(r'^(?P<object_id>.*)/moderation', view='moderation', name='moderation'),
    url(r'^(?P<object_id>.*)/moderation_ajax', view='moderation_ajax', name='moderation_ajax'),
    url(r'^(?P<object_id>.*)/search', view='search', name='search'),
    url(r'(?P<object_id>.*)/?$', view='main', name='main_current'),
)
