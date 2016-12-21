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
"""Custom filters for build_perf app"""
from django import template

register = template.Library()


@register.filter
def get_item(hashable, key):
    try:
        return hashable[key]
    except:
        raise Exception("FAIL: %s of len %s (%s)" % (key, len(hashable), hashable))


@register.filter
def get_attr(obj, attr):
    return getattr(obj, attr)

@register.filter
def has_attr(obj, attr):
    return hasattr(obj, attr)

@register.filter
def gv_data_convert(value, src_unit=None):
    from datetime import timedelta
    if src_unit == 'usec' or src_unit == 'timedelta':
        if src_unit == 'usec':
            secs = int(value / 1000000)
            usecs = int(value % 1000000)
        else:
            secs = int(value.total_seconds())
            usecs = value.microseconds
        hms = [int(secs / 3600), int((secs % 3600) / 60), secs % 60, int(usecs / 1000)]
        return hms
    elif src_unit == 'kib':
      return value / 1024
    return value

@register.filter
def gv_data_to_str(value, src_unit=None):
    if src_unit == 'kib':
        if value < 1024:
            return '%d kiB' % value
        elif value < 1048576:
            return '%.1f MiB' % (float(value) / 1024)
        else:
            return '%.1f GiB' % (float(value) / 1048576)
    elif src_unit == 'usec' or src_unit == 'timedelta':
        hms = gv_data_convert(value, src_unit)
        if hms[0] > 0:
            return '%d:%02d:%02d.%d' % (hms[0], hms[1], hms[2], hms[3] / 100)
        else:
            return '%02d:%02d.%d' % (hms[1], hms[2], hms[3] / 100)
    return str(value)
