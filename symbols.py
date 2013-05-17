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

class Lib(object):
    def __init__(self, libm, mangler=unary_math_suffix, have_symbol=None):
        """
        :param mangler: (name, llvm_type) -> math_name
        """
        self.libm = libm
        self.mangle = mangler
        self._have_symbol = have_symbol

    def have_symbol(self, cname):
        if self._have_symbol is None:
            return self.get_libm_symbol(cname)
        return self._have_symbol(self.libm, cname)

class CtypesLib(Lib):
    def get_libm_symbol(self, cname):
        func = getattr(self.libm, cname, None)
        if func is not None:
            return ctypes.cast(func, ctypes.c_void_p).value

class LLVMLib(Lib):
    def get_libm_symbol(self, cname):
        try:
            return self.libm.get_function_named(cname)
        except llvm.LLVMException:
            return None

def get_symbols(library, libm):
    """
    Populate a dict with runtime addressed of math functions from a given
    ctypes library.

    :param library: math_support.Library to add symbols to
    :param libm: ctypes or LLVM library of math functions
    """
    for types, funcs in unary:
        for ty in types:
            for name in funcs:
                if library.get_symbol(name, ty, ty):
                    continue
                cname = libm.mangle(name, ty)
                if libm.have_symbol(cname):
                    symbol = libm.get_libm_symbol(cname)
                    library.add_symbol(name, ty, ty, symbol)

    return library