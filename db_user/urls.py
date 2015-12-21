from django.conf.urls import patterns, url

from db_user import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
]
