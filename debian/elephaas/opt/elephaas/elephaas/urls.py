from django.conf import settings
from django.conf.urls import patterns, include, url
from django.contrib.auth.models import User, Group
from django.contrib import admin

from elephaas import views

admin.autodiscover()

# remove "Auth" menu's from admin if we're not using the default auth system.
# This lets us ignore that menu if relying on LDAP or some other optional
# auth engine.

if ('django.contrib.auth.backends.ModelBackend' 
    not in settings.AUTHENTICATION_BACKENDS):
    admin.site.unregister(User)
    admin.site.unregister(Group)

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^admin/', include(admin.site.urls)),
]
