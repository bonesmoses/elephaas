from django.conf.urls import patterns, url

from db_user import views

urlpatterns = patterns('',
    url(r'^$', views.index, name='index'),
)
