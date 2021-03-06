from django.http import HttpResponseBadRequest
from django.conf.urls import url, include

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^(?P<latest_version>[0-9.]+)$', views.index, name='index_2'),
    url(r'^search/$', views.search, name='search'),
    url(r'^testrun_filter/$', views.testrun_filter, name='testrun_filter'),
    url(r'^testcase_filter/$', views.testcase_filter, name='testcase_filter'),
    url(r'^testrun/(?P<id>[0-9]+)$', views.testrun, name='testrun'),
    url(r'^testrun/', lambda x: HttpResponseBadRequest(), name='base_testrun'),
    url(r'^testreport/(?P<release>[\w.]+)$', views.testreport, name='testreport'),
    url(r'^testreport/(?P<release>[\w.]+)/(?P<testplan>[0-9]+)/(?P<target>[\w.-]+)/(?P<hw>[\w.-]+)$', views.planenv, name='plan_env'),
    url(r'^testreport/', lambda x: HttpResponseBadRequest(), name='base_testreport'),
    url(r'^xhr_tables/', include('charts.tables'))
]
