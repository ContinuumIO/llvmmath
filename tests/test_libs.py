# -*- coding: utf-8 -*-
from __future__ import print_function, division, absolute_import

import types

import numpy as np

from numba.support.math_support import ltypes, libs, llvm_support, symbols
from numba.support.math_support.tests import test_support

# ______________________________________________________________________

np_integral = ['i', 'l', np.longlong]
np_floating = ['f', 'd', np.float128]
np_complexes = [np.complex64, np.complex128, np.complex256]

npy_typemap = {
    ltypes.integral: np_integral,
    ltypes.floating: np_floating,
    ltypes.complexes: np_complexes,
}

lower, upper = 1, 10

def get_idata(dtype):
    return np.arange(lower, upper, dtype=dtype) # poor test data

def get_cdata(dtype):
    return np.arange(lower, upper, dtype=dtype) + 0.2j

# ______________________________________________________________________

ufunc_map = {
    'asin': 'arcsin',
    'acos': 'arccos',
    'atan': 'arctan',
    'asinh': 'arcsinh',
    'acosh': 'arccosh',
    'atanh': 'arctanh',
    'atan2': 'arctan2',
}

def run(libm, name, ty, dtype):
    print("Running %s %s" % (name, ty))
    cname = libs.mathcode_mangler(name, ty)

    npy_name = ufunc_map.get(name, name)
    npy_func = getattr(np, npy_name)
    func = getattr(libm, cname)

    test_data = get_idata(dtype)
    out = np.empty(upper - lower, dtype)

    for i in range(upper - lower):
        out[i] = func(test_data[i])

    npy_out = npy_func(test_data)
    assert np.allclose(out, npy_out), (name, ty, dtype, npy_out - out)

# ______________________________________________________________________

def run_ints(libm):
    for name in symbols.unary_integral:
        for ty, dtype in zip(ltypes.integral, np_integral):
            run(libm, name, ty, dtype)

def run_floats(libm):
    for name in symbols.unary_floating:
        for ty, dtype in zip(ltypes.floating, np_floating):
            run(libm, name, ty, dtype)

def test_llvm_library():
    lib = libs.math_library
    assert not lib.missing, lib.missing

    engine, module, pm = test_support.make_llvm_context()
    libm = types.ModuleType('libm')
    llvm_support.wrap_llvm_module(lib.module, engine, libm)

    print(libm.npy_sinl(10.0))

    # run_int_tests(libm)
    run_floats(libm)

test_llvm_library()