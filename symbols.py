# -*- coding: utf-8 -*-

"""
Math symbols and signatures.
"""

from __future__ import print_function, division, absolute_import

import os
import ctypes
import collections
from itertools import imap

from numba import *
from llvm.core import *

map = lambda f, xs: list(imap(f, xs))

# ______________________________________________________________________
# Unary functions

unary_integral = set(['abs'])

# double complex csin(double complex), ...
unary_complex = set([
    'sin', 'cos', 'tan', 'acos', 'asin', 'atan',
    'sinh', 'cosh', 'tanh', 'asinh', 'acosh', 'atanh',
    'sqrt', 'log', 'log2', 'log10', 'exp', 'exp2', 'expm1',
    'log1p', 'abs',
])

# double sin(double), float sinf(float), long double sinl(long double)
# TODO: erf, erfc, gamma, lgamme
unary_floating = unary_complex | set(['floor', 'ceil', 'rint', 'atan2'])

# ______________________________________________________________________
# Unary signatures

tollvm = lambda ty: ty.to_llvm()
integral  = map(tollvm, (int_, long_, longlong))
floating  = map(tollvm, (float32, float64, float128))
complexes = map(tollvm, (complex64, complex128, complex256))

unary = [
    (integral, unary_integral),
    (floating, unary_floating),
    (complexes, unary_complex),
]

# ______________________________________________________________________
# Naming

_ints = {
    ctypes.sizeof(ctypes.c_longlong) * 8: 'll',
    ctypes.sizeof(ctypes.c_long) * 8:     'l',  # this should override longlong
    ctypes.sizeof(ctypes.c_int) * 8:      '',   # this should override long
}
_floats = { TYPE_DOUBLE: '', TYPE_FLOAT: 'f' }

_int_name     = lambda name, ty: _ints.get(ty.width, '') + name
_float_name   = lambda name, ty: name + _floats.get(ty.kind, 'l')
_complex_name = lambda name, ty: 'c' + _float_name(name, ty.elements[0])

float_kinds = (TYPE_FLOAT, TYPE_DOUBLE, TYPE_X86_FP80, TYPE_FP128, TYPE_PPC_FP128)

def absname(ltype):
    if ltype.kind == TYPE_INTEGER:
        return _int_name('abs', ltype)
    elif ltype.kind in float_kinds:
        return _float_name('fabs', ltype)
    else:
        assert ltype.kind == TYPE_STRUCT, ltype
        return _complex_name('abs', ltype)

def unary_math_suffix(name, ltype):
    if name == 'abs':
        return absname(ltype)
    elif ltype.kind in float_kinds:
        assert name in unary_floating
        return _float_name(name, ltype)
    else:
        assert ltype.kind == TYPE_STRUCT, ltype
        assert name in unary_complex
        return _complex_name(name, ltype)

# ______________________________________________________________________
# Retrieve symbols
have_symbol = lambda libm, cname: hasattr(libm, cname)

def get_symbols(libm, mangler=unary_math_suffix, have_symbol=have_symbol):
    """
    Populate a dict with runtime addressed of math functions from a given
    ctypes library.

    :param libm: ctypes library of math functions
    :param mangler: (name, llvm_type) -> math_name
    :returns: { func_name : { return_type, argtype) : func_addr } }
    """
    missing = []
    funcptrs = collections.defaultdict(dict)

    def add_func(name, cname, ty):
        func = getattr(libm, cname)
        p = ctypes.cast(func, ctypes.c_void_p).value
        sty = str(ty) # llvm types don't hash properly
        funcptrs[name][sty, sty] = p

    for types, funcs in unary:
        for ty in types:
            for name in funcs:
                cname = mangler(name, ty)
                if have_symbol(libm, cname):
                    # print("found", cname)
                    add_func(name, cname, ty)
                else:
                    missing.append((cname, ty))
                    # print("Missing symbol: %s %s(%s)" % (ty, cname, ty))

    return funcptrs, missing