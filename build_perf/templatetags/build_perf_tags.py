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
from build_perf.templatetags.build_perf_filters import gv_data_convert

register = template.Library()

@register.assignment_tag
def strcat(*args):
    """Concatenate strings"""
    return ''.join([str(arg) for arg in args])


@register.simple_tag
def modify_query_param(request, *args, **kwargs):
    """Add modify query parameters of the request"""
    # Extend kwargs: args can be used for "dynamic" parameter names
    for i in xrange(0, len(args), 2):
        kwargs[args[i]] = args[i + 1]

    # Modify parameters
    params = request.GET.copy()
    for name, val in kwargs.iteritems():
        if val is None:
            if name in params:
                del params[name]
        else:
            params[name] = val
    return params.urlencode()

@register.simple_tag
def gv_datarow(values, src_unit, row_len):
    """Convert input values into a list of values for dataRow of Google
       visualization API"""
    cnt = 0
    ret = ''
    for value in values:
        cnt += 1
        ret += str(gv_data_convert(value, src_unit))
        ret += ','
    return ret + 'null,' * (row_len - cnt)
