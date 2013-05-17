# -*- coding: utf-8 -*-

"""
Benchmark some math implementations.
"""

from __future__ import print_function, division, absolute_import

import time
import ctypes

from numba import *
from numba.support import ctypes_support
from numba.support.math_support import symbols, math_support, libs, llvm_support

import numpy as np

N = 10000
SIZE = 1024

def _run(restype, argtype, funcname, ptr):
    crestype = llvm_support.map_llvm_to_ctypes(restype)
    cargtype = llvm_support.map_llvm_to_ctypes(argtype)
    cfunctype = ctypes.CFUNCTYPE(crestype, cargtype)
    cfunc = ctypes.cast(ptr, cfunctype)

    dout = ctypes_support.from_ctypes_type(crestype).get_dtype()
    din  = ctypes_support.from_ctypes_type(cargtype).get_dtype()
    out = np.empty(SIZE, dtype=dout)
    in_ = np.arange(SIZE, dtype=din)

    @jit(void(), nopython=True)
    def call_in_loop():
        for _ in range(N):
            for i in range(SIZE):
                out[i] = cfunc(in_[i])

    t = time.time()
    call_in_loop()
    t = time.time() - t
    # print(call_in_loop.lfunc)
    print("%-5s %.5f seconds (%s, %s)" % (funcname, t, restype, argtype))

def run(library):
    funcs = ['sin', 'cos', 'tan', 'log', 'sqrt', 'cosf', 'atanh']
    for funcname in funcs:
        for ty in symbols.floating[:2]:
            ptr = library.get_symbol(funcname, ty, ty)
            assert ptr is not None, (funcname, str(ty))
            _run(ty, ty, funcname, ptr)

def print_pointers():
    def p(d):
        for k, v in sorted(d.items()):
            print(k[1], hex(v))
    print("open")
    p(math_support.openlibm_library['atanh'])
    print("libm")
    p(math_support.libm_library['atanh'])
    print("umath")
    p(math_support.umath_library['atanh'])

if __name__ == '__main__':
    print("llvm lib")
    run(libs.llvm_library)
    print()

    print("umath")
    run(libs.umath_library)
    print()

    print("openlibm")
    run(libs.openlibm_library)
    print()

    print("libm")
    run(libs.libm_library)
