from django.conf.urls import include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^build_perf/', include('build_perf.urls', namespace="build_perf")),
    url(r'', include('charts.urls', namespace="charts"))
]
