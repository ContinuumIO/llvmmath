# -*- coding: utf-8 -*-

"""
Support for math as a postpass on LLVM IR.
"""

from __future__ import print_function, division, absolute_import

import os
import ctypes.util
from itertools import imap
import collections

from numba import *
from numba.support import ctypes_support, llvm_support
from numba.support.math_support import symbols

import llvm.core
import numpy.core.umath

# openlibm = ctypes.CDLL(ctypes.util.find_library("openlibm"))

umath = ctypes.CDLL(numpy.core.umath.__file__)
umath_mangler = lambda name, ty: 'npy_' + symbols.unary_math_suffix(name, ty)

# libm = ctypes.CDLL(ctypes.util.find_library("m"))

# ______________________________________________________________________

def link_llvm_math_intrinsics(engine, module, library):
    """
    Add a runtime address for all global functions named numba.math.*
    """
    # find all known math intrinsics and implement them.
    for gv in module.list_globals():
        name = gv.getName()
        if name.startswith("numba.math."):
            assert not gv.getInitializer()
            assert gv.type.kind == llvm.core.TYPE_FUNCTION

            signatures = library[gv.name]
            restype = gv.return_type
            argtype = gv.args[0]

            ptr = signatures[restype, argtype]
            engine.addGlobalMapping(gv, ptr)