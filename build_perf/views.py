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
from django.views.generic import DetailView, ListView

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
    list_fields = OrderedDict([('id', 'ID'),
                               ('product', 'Product'),
                               ('tester_host', 'Host'),
                               ('start_time', 'Start time'),
                               ('git_branch', 'Branch'),
                               ('git_commit', 'Commit'),
                               ('git_commit_count', 'Commit number'),
                               ('elapsed_time', 'Elapsed time')])

    def get_queryset(self):
        params = self.request.GET.dict()
        self.paginate_by = self.request.GET.get('items_per_page', '50')
        self.ordering = self.request.GET.get('order_by', 'start_time')
        self.filters = dict([(n, v) for n, v in self.request.GET.items() if \
                            n in self.list_fields])
        # Set columns
        self.columns = []
        cols = self.request.GET.getlist('column') or self.list_fields.keys()
        if not 'id' in cols:
            # Always show ID
            cols.insert(0, 'id')
        for field in cols:
            if field in self.filters:
                continue
            if (not field.startswith('git_commit') or
                ('git_commit' not in self.filters and
                 'git_commit_count' not in self.filters)):
                self.columns.append(field)
        queryset = BPTestRun.objects.filter(**self.filters).order_by(self.ordering).values_list(*self.columns)
        self.total_row_count = len(queryset)
        return queryset

    def get_context_data(self, **kwargs):
        context = super(TestRunList, self).get_context_data(**kwargs)
        context['order_by'] = self.ordering.lstrip('-')
        if not self.ordering.startswith('-'):
            context['reverse_order'] = '-' + self.ordering
        else:
            context['reverse_order'] = self.ordering.lstrip('-')

        # Add fields to show
        context['filters'] = OrderedDict()
        for field in self.filters:
            context['filters'][field] = (self.list_fields[field], self.filters[field])
        context['columns'] = OrderedDict()
        for field in self.columns:
            context['columns'][field] = self.list_fields[field]
        context['filter_params'] = self.request.GET.urlencode()
        context['total_row_count'] = self.total_row_count

        return context


class TestRunDetails(DetailView):
    """Index page listing all tester hosts"""
    model = BPTestRun

    def get(self, query, *args, **kwargs):
        return HttpResponse("Test run details page coming soon...")
