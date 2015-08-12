from django.conf.urls import patterns, include, url
from django.contrib.auth.models import User, Group

from django.contrib import admin
admin.autodiscover()

# remove "Auth" menu's from admin

admin.site.unregister(User)
admin.site.unregister(Group)

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'pg_admin.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^$', 'pg_admin.views.index', name='index'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^password/', include('db_user.urls', namespace="db_user")),
)
