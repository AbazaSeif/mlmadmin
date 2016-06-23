from api.views import UserViewSet, MlmViewSet
from django.conf import settings
from django.conf.urls import patterns, include, url
from django.views.generic.base import RedirectView
from rest_framework import routers
from rest_framework.authtoken import views

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()


# Routers provide an easy way of automatically determining the URL conf.
router = routers.DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'mlm', MlmViewSet)


urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'mysite.views.home', name='home'),
    # url(r'^mysite/', include('mysite.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^admin/', include(admin.site.urls)),
    (r'^media/(?P<path>.*)$', 'django.views.static.serve',{'document_root': settings.MEDIA_ROOT}),
    (r'^accounts/$', 'django.contrib.auth.views.login'),
    (r'^accounts/login/$', 'django.contrib.auth.views.login'),
    (r'^mlmadmin/', include('mlmadmin.urls')),
    (r'^$', RedirectView.as_view(url='/mlmadmin/')),
    (r'^accounts/profile/$', RedirectView.as_view(url='/mlmadmin/')),
    url(r'^api/', include(router.urls)),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^api-token-auth/', views.obtain_auth_token),
)
