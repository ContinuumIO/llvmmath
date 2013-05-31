# -*- coding: utf-8 -*-

"""
Benchmark some math implementations.
"""

from __future__ import print_function, division, absolute_import

import time
import ctypes

from numba import *
from . import symbols, linking, libs, llvm_support

import numpy as np

N = 10000
SIZE = 1024

assert False, "Update"

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


if __name__ == '__main__':
    libs = [libs.get_mathlib_so(), libs.get_umath(),
            libs.get_openlibm(), libs.get_libm()]
    names = ["mathcode/", "umath", "openlibm", "libm"]

    for lib, name in zip(libs, names):
        print(name)
        run(lib)
        print()
