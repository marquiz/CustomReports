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
"""Models of build_perf app"""
from django.db import models
from django.forms import ModelForm

class BPTestRun(models.Model):
    """Results from one oe-build-perf-test run"""
    product = models.CharField(max_length=60)
    tester_host = models.CharField(max_length=64)
    start_time = models.DateTimeField()
    elapsed_time = models.DurationField()
    git_branch = models.CharField(max_length=50)
    git_commit = models.CharField(max_length=40)
    git_commit_count = models.IntegerField()


class BPTestCaseResult(models.Model):
    """Test rasults of one build performance test case"""
    FAILURE = 'FA'
    SUCCESS = 'SU'
    ERROR = 'ER'
    SKIPPED = 'SK'
    STATUS_CHOICES = ((FAILURE, 'FAILURE'),
                      (SUCCESS, 'SUCCESS'),
                      (ERROR, 'ERROR'),
                      (SKIPPED, 'SKIPPED'))
    class Meta:
        ordering = ['name']

    test_run = models.ForeignKey('BPTestRun', on_delete=models.CASCADE)
    name = models.CharField(max_length=40)
    description = models.CharField(max_length=120)
    status = models.CharField(max_length=2, choices=STATUS_CHOICES)
    start_time = models.DateTimeField()
    elapsed_time = models.DurationField()


class IOStatBase(models.Model):
    """I/O stat figures"""
    cancelled_write_bytes = models.BigIntegerField()
    rchar = models.BigIntegerField()
    read_bytes = models.BigIntegerField()
    syscr = models.IntegerField()
    syscw = models.IntegerField()
    wchar = models.BigIntegerField()
    write_bytes = models.BigIntegerField()


class RusageBase(models.Model):
    """Resource usage from getrusage"""
    ru_utime = models.DurationField()
    ru_stime = models.DurationField()
    ru_maxrss = models.IntegerField()
    ru_minflt = models.IntegerField()
    ru_majflt = models.IntegerField()
    ru_inblock = models.IntegerField()
    ru_oublock = models.IntegerField()
    ru_nvcsw = models.IntegerField()
    ru_nivcsw = models.IntegerField()


class BPMeasurement(models.Model):
    """Base cleas for build perf measurements"""
    test_result = models.ForeignKey('BPTestCaseResult',
                                    on_delete=models.CASCADE)
    name = models.CharField(max_length=20)
    legend = models.CharField(max_length=80)

class SysResMeasurement(BPMeasurement):
    """One measurement of system resources"""
    start_time = models.DateTimeField()
    # Allow empty time for failed tests
    elapsed_time = models.DurationField(null=True, blank=True)


class SysResIOStat(IOStatBase):
    """I/O stat for system resource measurements"""
    measurement = models.OneToOneField('SysResMeasurement',
                                       on_delete=models.CASCADE)


class SysResRusage(RusageBase):
    """Resource usage for system resource measurements"""
    measurement = models.OneToOneField('SysResMeasurement',
                                       on_delete=models.CASCADE)


class DiskUsageMeasurement(BPMeasurement):
    """Measurement of disk size of a file/directory"""
    size = models.IntegerField()


class BuildStatRecipe(models.Model):
    """Buildstats of one recipe"""
    measurement = models.ForeignKey('SysResMeasurement',
                                    on_delete=models.CASCADE)
    name = models.CharField(max_length=60)
    version = models.CharField(max_length=60)
    revision = models.CharField(max_length=5)
    epoch = models.CharField(max_length=5, blank=True)


class BuildStatTask(models.Model):
    """Buildstats of one task"""
    FAILED = 'F'
    PASSED = 'P'
    STATUS_CHOICES = ((FAILED, 'Failed'),
                      (PASSED, 'Passed'))

    recipe = models.ForeignKey('BuildStatRecipe', on_delete=models.CASCADE)
    name = models.CharField(max_length=40)
    start_time = models.DateTimeField()
    elapsed_time = models.DurationField()
    status = models.CharField(max_length=1, choices=STATUS_CHOICES)


class BuildStatIOStat(IOStatBase):
    """I/O stat from buildstats"""
    task = models.ForeignKey('BuildStatTask', on_delete=models.CASCADE)


class BuildStatRusage(RusageBase):
    """Rusage from buildstats"""
    SELF = 'S'
    CHILDREN = 'C'
    WHO_CHOICES = ((SELF, 'Self'),
                   (CHILDREN, 'Children'))
    task = models.ForeignKey('BuildStatTask', on_delete=models.CASCADE)
    who = models.CharField(max_length=1, choices=WHO_CHOICES)


class GitImportTip(models.Model):
    """Helper class for add_build_perf_test_results.py to store the last
       imported commits of branches"""
    branch = models.CharField(max_length=80, unique=True)
    commit = models.CharField(max_length=40)


#{ Forms for add_build_perf_test_result.py

class BPTestRunForm(ModelForm):
    class Meta:
        model = BPTestRun
        fields = '__all__'


class BPTestCaseResultForm(ModelForm):
    class Meta:
        model = BPTestCaseResult
        fields = '__all__'


class SysResMeasurementForm(ModelForm):
    class Meta:
        model = SysResMeasurement
        fields = '__all__'


class SysResIOStatForm(ModelForm):
    class Meta:
        model = SysResIOStat
        fields = '__all__'


class SysResRusageForm(ModelForm):
    class Meta:
        model = SysResRusage
        fields = '__all__'


class DiskUsageMeasurementForm(ModelForm):
    class Meta:
        model = DiskUsageMeasurement
        fields = '__all__'


class BuildStatRecipeForm(ModelForm):
    class Meta:
        model = BuildStatRecipe
        fields = '__all__'


class BuildStatTaskForm(ModelForm):
    class Meta:
        model = BuildStatTask
        fields = '__all__'


class BuildStatIOStatForm(ModelForm):
    class Meta:
        model = BuildStatIOStat
        fields = '__all__'


class BuildStatRusageForm(ModelForm):
    class Meta:
        model = BuildStatRusage
        fields = '__all__'
#}
