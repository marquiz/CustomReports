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
"""Views for build_perf app"""
from collections import OrderedDict
from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import ListView

from .models import BPTestRun


def index(request):
    """Index page listing all tester hosts"""
    fields = ('product', 'tester_host', 'git_branch')
    prod_list = BPTestRun.objects.values_list(*fields).distinct().order_by(*fields)
    products = OrderedDict()
    for prod, host, branch in prod_list:
        if not prod in products:
            products[prod] = OrderedDict()
        if not host in products[prod]:
            products[prod][host] = []
        products[prod][host].append(branch)

    return render(request, 'build_perf/index.html', {
        'products': products,
        })


class TestRunList(ListView):
    """Index page listing all tester hosts"""
    model = BPTestRun

    def get(self, query, *args, **kwargs):
        return HttpResponse("List of test runs coming soon...")
