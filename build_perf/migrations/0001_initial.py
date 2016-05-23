# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='BPMeasurement',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=20)),
                ('legend', models.CharField(max_length=80)),
            ],
        ),
        migrations.CreateModel(
            name='BPTestCaseResult',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=40)),
                ('description', models.CharField(max_length=120)),
                ('status', models.CharField(max_length=2, choices=[(b'FA', b'FAILURE'), (b'SU', b'SUCCESS'), (b'ER', b'ERROR'), (b'SK', b'SKIPPED')])),
                ('start_time', models.DateTimeField()),
                ('elapsed_time', models.DurationField()),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='BPTestRun',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('product', models.CharField(max_length=60)),
                ('tester_host', models.CharField(max_length=64)),
                ('start_time', models.DateTimeField()),
                ('elapsed_time', models.DurationField()),
                ('git_branch', models.CharField(max_length=50)),
                ('git_commit', models.CharField(max_length=40)),
                ('git_commit_count', models.IntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='BuildStatRecipe',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=60)),
                ('version', models.CharField(max_length=60)),
                ('revision', models.CharField(max_length=5)),
                ('epoch', models.CharField(max_length=5, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='BuildStatTask',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=40)),
                ('start_time', models.DateTimeField()),
                ('elapsed_time', models.DurationField()),
                ('status', models.CharField(max_length=1, choices=[(b'F', b'Failed'), (b'P', b'Passed')])),
                ('recipe', models.ForeignKey(to='build_perf.BuildStatRecipe')),
            ],
        ),
        migrations.CreateModel(
            name='IOStatBase',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('cancelled_write_bytes', models.BigIntegerField()),
                ('rchar', models.BigIntegerField()),
                ('read_bytes', models.BigIntegerField()),
                ('syscr', models.IntegerField()),
                ('syscw', models.IntegerField()),
                ('wchar', models.BigIntegerField()),
                ('write_bytes', models.BigIntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='RusageBase',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('ru_utime', models.DurationField()),
                ('ru_stime', models.DurationField()),
                ('ru_maxrss', models.IntegerField()),
                ('ru_minflt', models.IntegerField()),
                ('ru_majflt', models.IntegerField()),
                ('ru_inblock', models.IntegerField()),
                ('ru_oublock', models.IntegerField()),
                ('ru_nvcsw', models.IntegerField()),
                ('ru_nivcsw', models.IntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='BuildStatIOStat',
            fields=[
                ('iostatbase_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='build_perf.IOStatBase')),
                ('task', models.ForeignKey(to='build_perf.BuildStatTask')),
            ],
            bases=('build_perf.iostatbase',),
        ),
        migrations.CreateModel(
            name='BuildStatRusage',
            fields=[
                ('rusagebase_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='build_perf.RusageBase')),
                ('who', models.CharField(max_length=1, choices=[(b'S', b'Self'), (b'C', b'Children')])),
                ('task', models.ForeignKey(to='build_perf.BuildStatTask')),
            ],
            bases=('build_perf.rusagebase',),
        ),
        migrations.CreateModel(
            name='DiskUsageMeasurement',
            fields=[
                ('bpmeasurement_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='build_perf.BPMeasurement')),
                ('size', models.IntegerField()),
            ],
            bases=('build_perf.bpmeasurement',),
        ),
        migrations.CreateModel(
            name='SysResIOStat',
            fields=[
                ('iostatbase_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='build_perf.IOStatBase')),
            ],
            bases=('build_perf.iostatbase',),
        ),
        migrations.CreateModel(
            name='SysResMeasurement',
            fields=[
                ('bpmeasurement_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='build_perf.BPMeasurement')),
                ('start_time', models.DateTimeField()),
                ('elapsed_time', models.DurationField(null=True, blank=True)),
            ],
            bases=('build_perf.bpmeasurement',),
        ),
        migrations.CreateModel(
            name='SysResRusage',
            fields=[
                ('rusagebase_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='build_perf.RusageBase')),
                ('measurement', models.OneToOneField(to='build_perf.SysResMeasurement')),
            ],
            bases=('build_perf.rusagebase',),
        ),
        migrations.AddField(
            model_name='bptestcaseresult',
            name='test_run',
            field=models.ForeignKey(to='build_perf.BPTestRun'),
        ),
        migrations.AddField(
            model_name='bpmeasurement',
            name='test_result',
            field=models.ForeignKey(to='build_perf.BPTestCaseResult'),
        ),
        migrations.AddField(
            model_name='sysresiostat',
            name='measurement',
            field=models.OneToOneField(to='build_perf.SysResMeasurement'),
        ),
        migrations.AddField(
            model_name='buildstatrecipe',
            name='measurement',
            field=models.ForeignKey(to='build_perf.SysResMeasurement'),
        ),
    ]
