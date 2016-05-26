#!/usr/bin/python
#
# Script for importing results from oe-build-perf-test script into
# CustomReports.
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
"""Import oe-build-perf-test results"""
import argparse
import django
import json
import logging
import os
import shutil
import sys
import tempfile
from datetime import datetime, timedelta, tzinfo
from django.db import IntegrityError, transaction

sys.path.append(os.path.join(os.path.dirname(__file__), "customreports/"))
os.environ["DJANGO_SETTINGS_MODULE"] = "customreports.settings"
django.setup()

from build_perf.models import (BPTestRun, BPTestCaseResult,
                               DiskUsageMeasurement, SysResMeasurement,
                               SysResRusage, SysResIOStat,
                               BuildStatRecipe, BuildStatTask, BuildStatRusage,
                               BuildStatIOStat)


logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


class MyError(Exception):
    """Exception for handling errors in this script"""
    pass


def parse_args(argv):
    """Parse command line arguments"""
    descr = """
Script for importing results from oe-build-perf-test script into CustomReports.
The script is intended for development and testing purpoeses."""
    parser = argparse.ArgumentParser(
                description=descr,
                formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('-d', '--debug', action='store_true',
                        help='Enable debug level logging')
    parser.add_argument('results_path', metavar='RESULTS_PATH',
                        help="Results which to import")
    args = parser.parse_args(argv)
    args.results_path = os.path.abspath(args.results_path)
    return args


class TimeZone(tzinfo):
    """Simple fixed-offset tzinfo"""
    def __init__(self, seconds, name):
        self._offset = timedelta(seconds=seconds)
        self._name = name

    def utcoffset(self, dt):
        return self._offset

    def tzname(self, dt):
        return self._name

    def dst(self, dt):
        return None


def choice_lookup(value, choices_map):
    """Helper for mapping values to db-values"""
    if not value in choices_map:
        raise TypeError("Invalid choice value '{}' (not one of {})".format(
                            value, ', '.join(choices_map.keys())))
    return choices_map[value]


def to_datetime_obj(obj):
    """Helper for getting timestamps in datetime format"""
    if isinstance(obj, datetime):
        return obj
    else:
        return datetime.utcfromtimestamp(obj)

def to_timedelta_obj(obj):
    """Helper for getting elapsed time in timedelta format"""
    if isinstance(obj, timedelta):
        return obj
    else:
        return timedelta(seconds=obj)


def import_results_dir(results_dir):
    """Import results dir produced by oe-build-perf-test script"""
    log.info("Importing test results from {}".format(results_dir))

    # Read json file
    with open(os.path.join(results_dir, 'results.json')) as fobj:
        results = json.load(fobj)

    # Load buildstats
    for test in results['tests'].values():
        for measurement in test['measurements']:
            bs_fn = measurement['values'].get('buildstats_file')
            if bs_fn:
                with open(os.path.join(results_dir, bs_fn)) as fobj:
                    measurement['values']['buildstats'] = json.load(fobj)

    # Import test results data
    try:
        import_results(results)
    except (TypeError, IntegrityError) as err:
        log.error("Problems in input data: {}".format(err))
        raise MyError("Invalid results data!")

def import_results(results):
    """Import all data from a results dict into the database"""
    data = {}
    for field in ('product', 'tester_host', 'git_branch', 'git_commit',
                  'git_commit_count'):
        data[field] = str(results[field])
    data['start_time'] = to_datetime_obj(results['start_time'])
    data['elapsed_time'] = to_timedelta_obj(results['elapsed_time'])

    # Check if this testrun already exists in the DB
    if BPTestRun.objects.filter(**data).exists():
        log.warning("Test run results already found in DB, skipping import!")
        return None
    with transaction.atomic():
        testrun_obj = BPTestRun(**data)
        testrun_obj.save()
        for case_result in results['tests'].values():
            import_bptestcaseresult(case_result, testrun_obj)
        return testrun_obj

def import_bptestcaseresult(case_results, test_run):
    """Create BPTestCaseResult from results json data"""
    status_map = {'SUCCESS': BPTestCaseResult.SUCCESS,
                  'FAIL': BPTestCaseResult.FAILURE,
                  # Some old JSON reports might have 'FAIL' instead of 'FAILURE'
                  'FAILURE': BPTestCaseResult.FAILURE,
                  'ERROR': BPTestCaseResult.ERROR,
                  'SKIPPED': BPTestCaseResult.SKIPPED,
                  'UNEXPECTED_SUCCESS': BPTestCaseResult.SUCCESS,
                  'EXPECTED_FAILURE': BPTestCaseResult.FAILURE,
                  }
    status = choice_lookup(case_results['status'], status_map)

    data = {'name': case_results['name'],
            'description': case_results['description'],
            'status': status}
    if case_results['start_time'] is not None:
        data['start_time'] = to_datetime_obj(case_results['start_time'])
    if case_results['elapsed_time'] is not None:
        data['elapsed_time'] = to_timedelta_obj(case_results['elapsed_time'])
    result_obj = test_run.bptestcaseresult_set.create(**data)
    for meas in case_results['measurements']:
        if meas['type'] == 'diskusage':
            du_obj = DiskUsageMeasurement(test_result=result_obj,
                                          name=meas['name'],
                                          legend=meas['legend'],
                                          size=meas['values']['size'])
            du_obj.save()
        elif meas['type'] == 'sysres':
            import_sysresmeasurement(meas['name'], meas['legend'],
                                     meas['values'], result_obj)
        else:
            raise TypeError("Unknown measurement type {} in {} results".format(
                            mtype, case_results['name']))
    return result_obj

def import_sysresmeasurement(name, legend, values, test_result):
    """Import SysResMeasurement from json data"""
    data = {'test_result': test_result,
            'name': name,
            'legend': legend,
            'start_time': to_datetime_obj(values['start_time']),
            'elapsed_time': to_timedelta_obj(values['elapsed_time'])}
    meas_obj = SysResMeasurement(**data)
    meas_obj.save()

    # Import rusage
    data = {'measurement': meas_obj}
    data.update(values['rusage'])
    # We need to convert stime and utime to timedelta
    data['ru_stime'] = to_timedelta_obj(data['ru_stime'])
    data['ru_utime'] = to_timedelta_obj(data['ru_utime'])
    ru_obj = SysResRusage(**data)
    ru_obj.save()

    # Import IO stat
    if 'iostat' in values:
        data = {'measurement': meas_obj}
        data.update(values['iostat'])
        io_obj = SysResIOStat(**data)
        io_obj.save()

    # Import buildstats
    if 'buildstats' in values:
        for recipe in values['buildstats']:
            import_bs_recipe(recipe, meas_obj)

    return meas_obj


def import_bs_recipe(recipe_data, sysres_meas_obj):
    """Import BuildStatRecipe data from json-formatted buildstats"""
    data = {'name': recipe_data['name'],
            'version': recipe_data['version'],
            'revision': recipe_data['revision']}
    if recipe_data['epoch'] is not None:
        data['epoch'] = recipe_data['epoch']

    rec_obj = sysres_meas_obj.buildstatrecipe_set.create(**data)
    for task_name, task_data in recipe_data['tasks'].iteritems():
        import_bs_task(task_name, task_data, rec_obj)


def import_bs_task(task_name, task_data, recipe_obj):
    """Import BuildStatTask data"""
    status_map = {'PASSED': 'P',
                  'FAILED': 'F'}
    status = choice_lookup(task_data['status'], status_map)

    data = {'name': task_name,
            'start_time': to_datetime_obj(task_data['start_time']),
            'elapsed_time': to_timedelta_obj(task_data['elapsed_time'])}
    task_obj = recipe_obj.buildstattask_set.create(**data)

    # Import rusages
    for who, key in (('S', 'rusage'), ('C', 'child_rusage')):
        if task_data[key]:
            data = {'who': who}
            data.update(task_data[key])
            data['ru_stime'] = to_timedelta_obj(task_data[key]['ru_stime'])
            data['ru_utime'] = to_timedelta_obj(task_data[key]['ru_utime'])
            task_obj.buildstatrusage_set.create(**data)

    # Import IO stat
    if task_data['iostat']:
        task_obj.buildstatiostat_set.create(**task_data['iostat'])


def main(argv=None):
    """Script entry point"""
    args = parse_args(argv)

    if args.debug:
        log.setLevel(logging.DEBUG)

    ret = 1
    try:
        # Import test results data
        import_results_dir(args.results_path)
        ret = 0
    except MyError as err:
        if len(str(err)) > 0:
            log.error(str(err))

    return ret

if __name__ == '__main__':
    sys.exit(main())
