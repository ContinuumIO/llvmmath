# -*- coding: utf-8 -*-

"""
Naming of math functions.
"""

from __future__ import print_function, division, absolute_import

from . import ltypes
from llvm.core import *

# ______________________________________________________________________
# Default naming of external math functions

_ints = {
    ltypes.l_longlong.width: 'll',
    ltypes.l_long.width:     'l',  # this should override longlong
    ltypes.l_int.width:      '',   # this should override long
}
_floats = { TYPE_DOUBLE: '', TYPE_FLOAT: 'f' }

int_name     = lambda name, ty: _ints.get(ty.width, '') + name
float_name   = lambda name, ty: name + _floats.get(ty.kind, 'l')
complex_name = lambda name, ty: 'c' + float_name(name, ty.elements[0])

def absname(ltype):
    if ltype.kind == TYPE_INTEGER:
        return int_name('abs', ltype)
    elif ltypes.is_float(ltype):
        return float_name('fabs', ltype)
    else:
        return complex_name('abs', ltype)

def mathname(name, signature):
    ltype = signature.argtypes[0]
    if name == 'abs':
        return absname(ltype)
    elif ltypes.is_float(ltype):
        return float_name(name, ltype)
    else:
        return complex_name(name, ltype)
