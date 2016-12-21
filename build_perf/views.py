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
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import ExpressionWrapper, F
from django.db.models.fields import FloatField, IntegerField
from django.http import HttpResponse, Http404
from django.shortcuts import render
from django.views.generic import DetailView, ListView
from django.db.models import Count, Max, Min, Sum

from .models import BPTestRun, BPTestCaseResult, BPMeasurement
from .templatetags.build_perf_filters import gv_data_to_str

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


def testrun_list(request):
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

    params = request.GET.dict()

    # Get ordered list of items
    ordering = request.GET.get('order_by', 'start_time')
    filters = dict([(n, v) for n, v in request.GET.items() if \
                        n in list_fields])
    all_runs = BPTestRun.objects.filter(**filters).order_by(ordering)

    # Do pagination
    paginate_by = request.GET.get('items_per_page', '50')
    paginator = Paginator(all_runs, paginate_by)
    page = request.GET.get('page')
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    runs = page_obj.object_list

    # Set data columns
    columns = []
    cols = request.GET.getlist('column') or list_fields.keys()
    if not 'id' in cols:
        # Always show ID
        cols.insert(0, 'id')
    for field in cols:
        if field in filters:
            continue
        if (not field.startswith('git_commit') or
            ('git_commit' not in filters and
             'git_commit_count' not in filters)):
            columns.append((field, list_fields[field]))

    # Form data table
    table = []
    for run in runs.values_list(*[f for f, n in columns]):
        table.append(list(run))

    # Set measurement columns
    measurement_col_ids = {}
    measurement_cols = request.GET.getlist('measurement')
    if not measurement_cols:
        # Get all measurements
        measurements = BPMeasurement.objects.order_by('test_result__name').values_list('test_result__name', 'name').distinct()
        for i, (test, measurement) in enumerate(measurements):
            measurement_cols.append(test + ':' + measurement)
    if measurement_cols:
        for i, col in enumerate(measurement_cols):
            if col:
                test, measurement = col.split(':')
                measurement_col_ids[col] = i
                # Get quantity
                if hasattr(BPMeasurement.objects.filter(test_result__name=test, name=measurement).last(), 'sysresmeasurement'):
                    quantity = 'time'
                else:
                    quantity = 'size'
                columns.append((None, "%s: %s %s" % (test, measurement, quantity)))

    if measurement_col_ids:
        for i, run in enumerate(runs):
            extra = [None] * len(measurement_col_ids)
            for test, measurement, time, size in run.bptestcaseresult_set.values_list('name', 'bpmeasurement__name', 'bpmeasurement__sysresmeasurement__elapsed_time', 'bpmeasurement__diskusagemeasurement__size'):
                if not measurement:
                    continue
                key = test + ':' + measurement
                if key in measurement_col_ids:
                    value = time or size
                    unit = 'timedelta' if time else 'kib'
                    str_value = gv_data_to_str(value, unit)
                    extra[measurement_col_ids[key]] = str_value
            table[i].extend(extra)

    # Gather context data
    context = {}
    context['paginator'] = paginator
    context['page_obj'] = page_obj
    context['order_by'] = ordering.lstrip('-')
    if not ordering.startswith('-'):
        context['reverse_order'] = '-' + ordering
    else:
        context['reverse_order'] = ordering.lstrip('-')

    # Add fields to show
    context['filters'] = OrderedDict()
    for field in filters:
        context['filters'][field] = (list_fields[field], filters[field])
    context['columns'] = columns
    context['filter_params'] = request.GET.urlencode()
    context['row_data'] = table
    context['total_row_count'] = len(all_runs)

    return render(request, 'build_perf/bptestrun_list.html', context)


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
