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
import logging
import os
import sys


sys.path.append(os.path.join(os.path.dirname(__file__), "customreports/"))
os.environ["DJANGO_SETTINGS_MODULE"] = "customreports.settings"
django.setup()


logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


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


def main(argv=None):
    """Script entry point"""
    args = parse_args(argv)

    if args.debug:
        log.setLevel(logging.DEBUG)

    return 0

if __name__ == '__main__':
    sys.exit(main())
