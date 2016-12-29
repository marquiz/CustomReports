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
from subprocess import check_output

sys.path.append(os.path.join(os.path.dirname(__file__), "customreports/"))
os.environ["DJANGO_SETTINGS_MODULE"] = "customreports.settings"
django.setup()

from build_perf.models import (BPTestRun, BPTestCaseResult,
                               DiskUsageMeasurement, SysResMeasurement,
                               SysResRusage, SysResIOStat,
                               BuildStatRecipe, BuildStatTask, BuildStatRusage,
                               BuildStatIOStat, GitImportTip)


logging.basicConfig(level=logging.INFO)
log = logging.getLogger('main')


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

    parser.add_argument('--git', nargs="*", metavar="GIT_REV",
                        help="Assume that RESULTS_PATH is a (local) Git "
                             "repository, import data from local branches or "
                             "the given revision(s)")
    parser.add_argument('--git-fetch', action="store_true",
                        help="Run git fetch before import, useful when "
                             "combined with --remote")
    parser.add_argument('--git-remote', metavar="GIT_REMOTE",
                        nargs="?", const='',
                        help="Import remote branches from %(metavar)s instead "
                             "of local Git branches.")
    parser.add_argument('-F', '--force-meta', action='append', nargs=2,
                        help='Override test metadata, use with care!')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='Enable debug level logging')
    parser.add_argument('-D', '--debug2', action='store_true',
                        help='More verbose logging')
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

TIMEZONES = {'UTC': TimeZone(0, 'UTC'),
             'EET': TimeZone(7200, 'EET'),
             'EEST': TimeZone(10800, 'EEST')}


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
        return datetime.utcfromtimestamp(obj).replace(tzinfo=TIMEZONES['UTC'])

def to_timedelta_obj(obj):
    """Helper for getting elapsed time in timedelta format"""
    if isinstance(obj, timedelta):
        return obj
    else:
        return timedelta(seconds=obj)


def read_json_report(results_dir):
    """Read results and metadata from JSON files"""
    with open(os.path.join(results_dir, 'results.json')) as fobj:
        results = json.load(fobj)
    if os.path.exists(os.path.join(results_dir, 'metadata.json')):
        with open(os.path.join(results_dir, 'metadata.json')) as fobj:
            metadata = json.load(fobj)
    else:
        metadata = {'hostname': results['tester_host'],
                    'distro': {'id': results['product']},
                    'layers': {'meta': {'branch': results['git_branch'],
                                        'commit': results['git_commit'],
                                        'commit_count': results['git_commit_count']}}}
    return metadata, results


def import_results_dir(results_dir, force_meta=None):
    """Import results dir produced by oe-build-perf-test script"""

    # Read json file
    metadata, results = read_json_report(results_dir)
    if force_meta:
        for attr, val in force_meta:
            top = metadata
            keys = attr.split('.')
            for key in keys[:-1]:
                if not key in top:
                    top[key] = dict()
                top = top[key]
            top[keys[-1]] = val

    # Load buildstats
    for test in results['tests'].values():
        for measurement in test['measurements']:
            bs_fn = measurement['values'].get('buildstats_file')
            if bs_fn:
                with open(os.path.join(results_dir, bs_fn)) as fobj:
                    measurement['values']['buildstats'] = json.load(fobj)

    # Import test results data
    try:
        import_results(metadata, results)
    except (TypeError, IntegrityError) as err:
        log.error("Problems in input data: {}".format(err))
        raise MyError("Invalid results data!")

def import_results(metadata, results):
    """Import all data from a results dict into the database"""
    data = {'product': metadata['distro']['id'],
            'tester_host': metadata['hostname'],
            'git_branch': metadata['layers']['meta']['branch'],
            'git_commit': metadata['layers']['meta']['commit'],
            'git_commit_count': metadata['layers']['meta']['commit_count'],
            'start_time': to_datetime_obj(results['start_time']),
            'elapsed_time': to_timedelta_obj(results['elapsed_time'])
    }

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


def import_git(path, git_rev, force_meta):
    """Import all testruns from Git revision range"""
    tmpdir = tempfile.mkdtemp(prefix='git_worktree_')
    all_branches = get_git_branches(path) + get_git_branches(path, remote='')

    # Store last imported commit if we're importing complete branches
    git_ref = check_output(['git', 'rev-parse', '--symbolic-full-name',
                            git_rev], cwd=path).splitlines()
    if git_ref:
        git_ref = git_ref[0]
        if git_ref in all_branches:
            tip_obj, _ = GitImportTip.objects.get_or_create(branch=git_ref)
            tip_commit = tip_obj.commit
            if tip_commit:
                log.info("Starting after commit %s (%s)", tip_commit, git_rev)
    else:
        tip_obj = None
        tip_commit = ''

    try:
        rev_range = '%s..%s' % (tip_commit, git_rev) if tip_commit else git_rev
        rev_list = check_output(['git', 'rev-list', '--reverse', rev_range],
                                cwd=path).splitlines()
        log.info("Importing %d testruns from Git (%s)",
                 len(rev_list), git_rev)
        for rev in rev_list:
            log.info("Importing revision %s (of %s)", rev, git_rev)
            log.debug("Unpacking revision %s", rev)
            unpack_dir = os.path.abspath(os.path.join(tmpdir, rev))
            os.mkdir(unpack_dir)
            check_output('git archive %s | tar -x -C %s' % (rev, unpack_dir),
                         cwd=path, shell=True)
            import_results_dir(unpack_dir, force_meta)

            if tip_obj:
                tip_obj.commit = rev
                tip_obj.save()

            log.debug("Unlinking unpack dir")
            shutil.rmtree(unpack_dir)
    finally:
        shutil.rmtree(tmpdir)

def git_fetch(path, remote=None):
    """Run git fetch"""
    log.info("Running git fetch")
    cmd = ['git', 'fetch']
    if remote == '':
        cmd.append('--all')
    elif remote:
        cmd.append(remote)
    check_output(cmd, cwd=path)

def get_git_branches(path, remote=None):
    """Get list of branches"""
    cmd = ['git', 'for-each-ref', '--format=%(refname)']
    if remote is not None:
        cmd.append('refs/remotes/' + remote)
    else:
        cmd.append('refs/heads')
    return [r for r in check_output(cmd, cwd=path).splitlines() if
            r != str(remote) + '/HEAD']


def main(argv=None):
    """Script entry point"""
    args = parse_args(argv)

    if args.debug:
        log.setLevel(logging.DEBUG)
    if args.debug2:
        logging.getLogger().setLevel(logging.DEBUG)
        log.setLevel(logging.DEBUG)

    ret = 1
    try:
        # Import test results data
        if args.git is not None:
            if args.git_fetch:
                git_fetch(args.results_path, args.git_remote)
            if args.git:
                revisions = args.git
            else:
                revisions = get_git_branches(args.results_path, args.git_remote)
                log.info("Found %d branches: %s", len(revisions), revisions)
            for rev_range in revisions:
                import_git(args.results_path, rev_range, args.force_meta)
        else:
            log.info("Importing test results from {}".format(args.results_path))
            import_results_dir(args.results_path, args.force_meta)
        ret = 0
    except MyError as err:
        if len(str(err)) > 0:
            log.error(str(err))

    return ret

if __name__ == '__main__':
    sys.exit(main())
