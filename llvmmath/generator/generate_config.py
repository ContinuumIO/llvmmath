# -*- coding: utf-8 -*-

"""
Support llvmmath/mathcode/private/config.h
"""

from __future__ import print_function, division, absolute_import

import ctypes.util
from textwrap import dedent
from functools import partial
from os.path import join, dirname, abspath

root = dirname(abspath(__file__))
mathcode = join(dirname(root), 'mathcode')
private = join(mathcode, 'private')

need_define = [
    'SIN', 'COS', 'TAN', 'SINH', 'COSH', 'TANH', 'FABS', 'FLOOR',
    'CEIL', 'SQRT', 'LOG10', 'LOG', 'EXP', 'ASIN', 'ACOS', 'ATAN',
    'FMOD', 'MODF', 'FREXP', 'LDEXP', 'RINT', 'TRUNC', 'EXP2',
    'LOG2', 'ATAN2', 'POW', 'NEXTAFTER', 'COPYSIGN',
    # Complex
    'CREAL', 'CIMAG', 'CABS', 'CARG', 'CEXP', 'CSQRT', 'CLOG',
    'CCOS', 'CSIN', 'CPOW',
]

# ______________________________________________________________________

def define_macro(write, name, value=""):
    write("#define %s %s\n" % (name, value))

def generate_config(f):
    define = partial(define_macro, f.write)

    define("SIZEOF_PY_INTPTR_T", ctypes.sizeof(ctypes.c_void_p))
    define("SIZEOF_PY_LONG_LONG", ctypes.sizeof(ctypes.c_longlong))

    define_math(define)

    f.write(dedent("""
    #ifndef _NPY_NPY_CONFIG_H_
    #error config.h should never be included directly, include npy_config.h instead
    #endif
    """))

def define_math(define):
    libm = ctypes.CDLL(ctypes.util.find_library("m"))
    for suffix in ('', 'F', 'L'):
        for check_sym in need_define:
            symname = check_sym + suffix
            have = hasattr(libm, symname.lower())
            define('HAVE_' + symname, int(have))

if __name__ == '__main__':
    import sys
    generate_config(sys.stdout)
