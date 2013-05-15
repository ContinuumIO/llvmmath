# -*- coding: utf-8 -*-

"""
Benchmark some math implementations.
"""

from __future__ import print_function, division, absolute_import

import os
import time
import ctypes
from itertools import imap
import collections

from numba import *
from numba.support import ctypes_support, llvm_support
from numba.support.math_support import symbols, math_support

import llvm.core
import numpy.core.umath
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

    print("%-5s %.5f seconds (%s, %s)" % (funcname, t, restype, argtype))

def run(library):
    funcs = ['sin', 'cos', 'tan', 'log', 'sqrt', 'cosf', 'atanh']
    for funcname in funcs:
        impls = library[funcname]
        for types, ptr in sorted(impls.iteritems()):
            restype, argtype = types
            if argtype.kind not in (llvm.core.TYPE_FLOAT, llvm.core.TYPE_DOUBLE):
                continue

            _run(restype, argtype, funcname, ptr)

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
    print("umath")
    run(math_support.umath_library)
    print()

    print("openlibm")
    run(math_support.openlibm_library)
    print()

    print("libm")
    run(math_support.libm_library)
