#
# Copyright (c) 2016, Intel Corporation.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms and conditions of the GNU General Public License,
# version 2, as published by the Free Software Foundation.
#
# This program is distributed in the hope it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
"""URL configuration for build_perf app"""
from django.conf.urls import url

from . import views


urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^testruns$', views.TestRunList.as_view(), name='testrunlist'),
    url(r'^testruns/(?P<pk>.+)$', views.TestRunDetails.as_view(), name='testrundetails'),
    #url(r'^history$', views.HistoryView.as_view(), name='history'),
    url(r'^history$', views.history_view, name='history'),
    url(r'^trendchart$', views.trend_chart, name='trendchart'),
]
