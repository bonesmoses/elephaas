from django.conf.urls import patterns, include, url
from django.contrib.auth.models import User, Group
from django.contrib import admin

from elephaas import views

admin.autodiscover()

# remove "Auth" menu's from admin

admin.site.unregister(User)
admin.site.unregister(Group)

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^admin/', include(admin.site.urls)),
]
