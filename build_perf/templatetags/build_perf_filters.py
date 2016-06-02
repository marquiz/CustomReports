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
    return hashable[key]


@register.filter
def get_attr(obj, attr):
    return getattr(obj, attr)
