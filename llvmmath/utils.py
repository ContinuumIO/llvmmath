# -*- coding: utf-8 -*-

"""
Utilities
"""

from __future__ import print_function, division, absolute_import

def cached(f):
    result = []
    def wrapper(*args, **kwargs):
        if len(result) == 0:
            ret = f(*args, **kwargs)
            result.append(ret)

        return result[0]
    return wrapper
