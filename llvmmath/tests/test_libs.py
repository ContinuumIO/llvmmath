# -*- coding: utf-8 -*-
from __future__ import print_function, division, absolute_import

from functools import partial

import llvm.core as lc
import numpy as np

from llvmmath import ltypes, libs
from llvmmath.tests import support
from llvmmath.tests.support import test

# ______________________________________________________________________

np_integral = ['i', 'l', getattr(np, 'longlong', 'l')]
np_floating = ['f', 'd', getattr(np, 'float128', np.double)]
np_complexes = [np.complex64, np.complex128, getattr(np, 'complex256',
                                                     np.complex128)]

npy_typemap = {
    tuple(map(str, ltypes.integral)): np_integral,
    tuple(map(str, ltypes.floating)): np_floating,
    tuple(map(str, ltypes.complexes)): np_complexes,
}

lower, upper = 1, 10

def _get_idata(dtype):
    return np.arange(lower, upper, dtype=dtype) # poor test data

def _get_cdata(dtype):
    return np.arange(lower, upper, dtype=dtype) + 0.2j

def wrapper(get_data, npy_name, data):
    a = get_data(data)
    if npy_name.startswith('arc') and npy_name not in ('arccosh',):
        a = 0.99 / a
    return a

get_idata = partial(wrapper, _get_idata)
get_cdata = partial(wrapper, _get_cdata)

# ______________________________________________________________________

ufunc_map = {
    'asin' : 'arcsin',
    'acos' : 'arccos',
    'atan' : 'arctan',
    'asinh': 'arcsinh',
    'acosh': 'arccosh',
    'atanh': 'arctanh',
    'atan2': 'arctan2',
    'pow'  : 'power',
}

def run(c_func, name, sig, dtype):
    print("Running %s %s" % (name, sig))
    nargs = len(sig.argtypes)
    npy_name = ufunc_map.get(name, name)
    npy_func = getattr(np, npy_name)

    if sig.restype.kind == lc.TYPE_STRUCT:
        c_func = partial(support.call_complex_byref, c_func)
        test_data = get_cdata(npy_name, dtype)
    else:
        test_data = get_idata(npy_name, dtype)

    out = np.empty(upper - lower, dtype)

    for i in range(upper - lower):
        print([test_data[i]] * len(sig.argtypes))
        out[i] = c_func(*[test_data[i]] * nargs)

    npy_out = npy_func(*[test_data] * nargs)
    assert np.allclose(out, npy_out), (name, sig, dtype, npy_out - out)

# ______________________________________________________________________

def run_from_types(library, types):
    for name, signatures in library.symbols.items():
        sample_sig = list(signatures)[0]
        for ty, dtype in zip(types, npy_typemap[tuple(map(str, types))]):
            sig = ltypes.Signature(ty, [ty] * len(sample_sig.argtypes))
            if sig in signatures:
                ctypes_func = library.get_ctypes_symbol(name, sig)
                run(ctypes_func, name, sig, dtype)

@test
def test_math():
    lib = libs.get_mathlib_so()
    assert not lib.missing, lib.missing
    run_from_types(lib, ltypes.integral)
    run_from_types(lib, ltypes.floating)
    run_from_types(lib, ltypes.complexes)

@test
def test_abs():
    "Test abs() with negative numbers"
    lib = libs.get_mathlib_so()

    def get_syms(rtypes, types):
        for rty, ty in zip(rtypes, types):
            yield lib.get_ctypes_symbol('abs', ltypes.Signature(rty, [ty]))

    iabs, labs, llabs = get_syms(ltypes.integral, ltypes.integral)
    fabsf, fabs, fabsl = get_syms(ltypes.floating, ltypes.floating)
    cabsf, cabs, cabsl = get_syms(ltypes.floating, ltypes.complexes)

    # Integral
    assert iabs(-2) == labs(-2) == llabs(-2) == 2

    # Floating
    result = fabsf(-2.2), fabs(-2.2), fabsl(-2.2)
    assert np.allclose(result, [2.2] * 3)

    # Complex
    call = support.call_complex_byref
    x = -2.2 - 3.3j
    result = call(cabsf, x), call(cabs, x), call(cabsl, x)
    result = [r.value for r in result]
    assert np.allclose(result, [abs(x)] * 3), result