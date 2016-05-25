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
import sys
from datetime import datetime, timedelta
from django.db import IntegrityError, transaction

sys.path.append(os.path.join(os.path.dirname(__file__), "customreports/"))
os.environ["DJANGO_SETTINGS_MODULE"] = "customreports.settings"
django.setup()

from build_perf.models import BPTestRun


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


def import_results_dir(results_dir):
    """Import results dir produced by oe-build-perf-test script"""
    log.info("Importing test results from {}".format(results_dir))

    # Read json file
    with open(os.path.join(results_dir, 'results.json')) as fobj:
        results = json.load(fobj)

    # Import test results data
    try:
        import_results(results)
    except (TypeError, IntegrityError) as err:
        log.error("Problems in input data: {}".format(err))
        raise MyError("Invalid testrun data in results.json")

def import_results(results):
    """Import all data from a results dict into the database"""
    data = {}
    for field in ('product', 'tester_host', 'git_branch', 'git_revision'):
        data[field] = str(results[field])
    data['start_time'] = datetime.utcfromtimestamp(results['start_time'])
    data['elapsed_time'] = timedelta(seconds=results['elapsed_time'])

    # Check if this testrun already exists in the DB
    if BPTestRun.objects.filter(**data).exists():
        log.warning("Test run results already found in DB, skipping import!")
        return None
    with transaction.atomic():
        testrun_obj = BPTestRun(**data)
        testrun_obj.save()
        return testrun_obj


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
