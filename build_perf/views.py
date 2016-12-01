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
import logging
from collections import OrderedDict
from datetime import timedelta
from django.db.models import ExpressionWrapper, F
from django.db.models.fields import FloatField, IntegerField
from django.http import HttpResponse, Http404
from django.shortcuts import render
from django.views.generic import DetailView, ListView
from django.db.models import Count, Max, Min, Sum

from .models import BPTestRun, BPTestCaseResult, BPMeasurement

log = logging.getLogger('django')


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

    def get_context_data(self, **kwargs):
        context = super(TestRunDetails, self).get_context_data(**kwargs)
        # Add fields to show
        context['info_fields'] = [('product', 'Product'),
                                  ('tester_host', 'Host'),
                                  ('git_branch', 'Branch'),
                                  ('git_commit', 'Commit'),
                                  ('start_time', 'Start time'),
                                  ('elapsed_time', 'Elapsed time')]
        context['rusage_fields'] = [('ru_utime', 'User CPU time'),
                                    ('ru_stime', 'System CPU time'),
                                    ('ru_maxrss', 'Max. resident set size'),
                                    ('ru_minflt', 'Page reclaims'),
                                    ('ru_majflt', 'Page faults'),
                                    ('ru_inblock', 'Block input operations'),
                                    ('ru_oublock', 'Block output operations'),
                                    ('ru_nvcsw', 'Voluntary context switches'),
                                    ('ru_nivcsw', 'Involunt. context switches')]
        context['iostat_fields'] = [('read_bytes', 'Bytes read from storage'),
                                    ('write_bytes', 'Bytes written to storage'),
                                    ('rchar', 'Characters read'),
                                    ('wchar', 'Characters written'),
                                    ('syscr', 'Read syscalls'),
                                    ('syscw', 'Write syscalls'),
                                    ('cancelled_write_bytes', 'Cancelled write bytes')]
        return context


def _aggregate_measurement(product, tester_host, git_branch, test, measurement):
    meta = {'product': product,
            'tester_host': tester_host,
            'git_branch': git_branch,
            'test': test,
            'measurement': measurement}

    measurements = BPMeasurement.objects.filter(
        name=measurement,
        test_result__name=test,
        test_result__test_run__product=product,
        test_result__test_run__tester_host=tester_host,
        test_result__test_run__git_branch=git_branch)
    last = measurements.last()

    # Check type of measurement
    if hasattr(last, 'sysresmeasurement'):
        meta['title'] = "Time of %s" % last.legend
        meta['quantity'] = 'time'
        meta['unit'] = 'timedelta'
        data_field = 'sysresmeasurement__elapsed_time'
    else:
        meta['title'] = "Size of %s" % last.legend
        meta['quantity'] = 'size'
        meta['unit'] = 'kib'
        data_field = 'diskusagemeasurement__size'

    # Calculate average over commits
    data = []
    commits = measurements.order_by('test_result__test_run__git_commit_count').values_list(
        'test_result__test_run__git_commit_count', 'test_result__test_run__git_commit').distinct()

    max_samples = 0
    for commit_count, commit in commits:
        per_commit = measurements.filter(test_result__test_run__git_commit=commit)
        row = per_commit.aggregate(
            sum=Sum(data_field), count=Count(data_field), min=Min(data_field), max=Max(data_field))
        row['avg'] = row['sum'] / row['count']
        row['samples'] = per_commit.filter(**{data_field + '__isnull': False}).values_list(data_field, flat=True)
        if row['count'] > max_samples:
            max_samples = row['count']

        row['commit_count'] = commit_count
        row['commit'] = commit
        data.append(row)

    # Fill rest of meta data
    meta['max_samples'] = max_samples

    return meta, data


def trend_chart(request):
    """Show history trend chart of one measurement"""
    required_params = set(('product', 'tester_host', 'git_branch', 'test',
                           'measurement'))
    params = request.GET.dict()
    missing = required_params - set(params.keys())
    if missing:
        raise Http404("Missing parameters: %s" % ', '.join(missing))

    context = {}
    context['meta'], context['data'] = \
        _aggregate_measurement(params['product'],
                               params['tester_host'],
                               params['git_branch'],
                               params['test'],
                               params['measurement'])
    return render(request, 'build_perf/trend_chart.html', context)


def history_view(request):
    """Trend chart data"""
    filter_fields = OrderedDict([('product', 'Product'),
                                 ('tester_host', 'Host'),
                                 ('git_branch', 'Branch'),
                                ])
    context = {}
    context['tests'] = OrderedDict()

    params = request.GET.dict()
    missing = set(filter_fields.keys()) - set(params.keys())
    if missing:
        raise Http404("Missing parameters: %s" % ', '.join(missing))

    filters = dict(test_result__test_run__product=params['product'],
                   test_result__test_run__tester_host=params['tester_host'],
                   test_result__test_run__git_branch=params['git_branch'])
    m_list = BPMeasurement.objects.filter(**filters).order_by('test_result__name').values_list('test_result__name', 'name').distinct()

    measurement_cnt = 0
    for test, measurement in m_list:
        if not test in context['tests']:
            descr = BPTestCaseResult.objects.filter(name=test).last().description
            context['tests'][test] = {'description': descr, 'measurements': []}
        context['tests'][test]['measurements'].append(
            _aggregate_measurement(params['product'], params['tester_host'], params['git_branch'],
                                   test, measurement))
        context['tests'][test]['measurements'][-1][0]['chart_id'] = 'chart_%d' % measurement_cnt
        measurement_cnt +=1

    context['info'] = OrderedDict()
    for field, heading in filter_fields.items():
        context['info'][heading] = params[field]

    return render(request, 'build_perf/history.html', context)
