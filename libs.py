# -*- coding: utf-8 -*-

"""
Support for math as a postpass on LLVM IR.
"""

from __future__ import print_function, division, absolute_import

import os
import ctypes.util
from pprint import pprint
from os.path import join, dirname
import collections

from numba.support.math_support import symbols, build, ltypes, naming

import llvm.core
import numpy.core.umath

root = dirname(__file__)

# ______________________________________________________________________

class Library(object):
    def __init__(self):
        # # { func_name : { return_type, argtype) : link_obj } }
        self.symbols = collections.defaultdict(dict)
        self.missing = [] # (name, cname, sig)

    def add_symbol(self, name, sig, val):
        assert sig not in self.symbols[name], (sig, self.symbols)
        self.symbols[name][sig] = val

    def get_symbol(self, name, signature):
        return self.symbols.get(name, {}).get(signature)

    def __str__(self):
        result = []
        for symbol, d in sorted(self.symbols.iteritems()):
            for (rty, argtys), linkable in d.iteritems():
                result.append("%s %s(%s): %s" % (
                    rty, symbol, ", ".join(map(str, argtys)), linkable))
        return "Library(\n%s)" % "\n    ".join(result)

class LLVMLibrary(Library):
    def __init__(self, module):
        super(LLVMLibrary, self).__init__()
        self.module = module # LLVM math module

# ______________________________________________________________________
# openlibm

# print("---------- OPENLIBM -----------")
symbol_data = open(os.path.join(os.path.dirname(__file__), "Symbol.map")).read()
openlibm_symbols = set(word.rstrip(';') for word in symbol_data.split())
openlibm = ctypes.CDLL(ctypes.util.find_library("openlibm"))
olm_have_sym = lambda libm, cname: cname in openlibm_symbols
openlibm_library = symbols.get_symbols(
    Library(), symbols.CtypesLib(openlibm, have_symbol=olm_have_sym))

# pprint(openlibm_library.missing)

# ______________________________________________________________________
# NumPy umath

# print("---------- umath -----------")
umath = ctypes.CDLL(numpy.core.umath.__file__)
umath_mangler = lambda name, ty: 'npy_' + naming.mathname(name, ty)
umath_library = symbols.get_symbols(
    Library(), symbols.CtypesLib(umath, mangler=umath_mangler))

# ______________________________________________________________________
# System's libmath

# print("---------- libm -----------")
libm = ctypes.CDLL(ctypes.util.find_library("m"))
libm_library = symbols.get_symbols(Library(), symbols.CtypesLib(libm))

# ______________________________________________________________________

# print("---------- mathcode -----------")
def mathcode_mangler(name, sig):
    ty = sig.argtypes[0]
    if name == 'abs':
        absname = naming.absname(ty)
        if ty.kind == llvm.core.TYPE_INTEGER or ltypes.is_float(ty):
            return 'npy_' + absname # abs(), labs(), llabs()
        else:
            return 'nc_' + absname
    elif ty.kind == llvm.core.TYPE_STRUCT:
        return 'nc_' + naming.float_name(name, ty.elements[0])
    else:
        return umath_mangler(name, sig)

dylib = 'mathcode' + build.find_shared_ending()
llvmmath = ctypes.CDLL(join(root, 'mathcode', dylib))
llvm_library = symbols.get_symbols(
    Library(), symbols.CtypesLib(llvmmath, mathcode_mangler))

# Load llvmmath as bitcode
lmath = build.load_llvm_asm()
math_library = symbols.get_symbols(LLVMLibrary(lmath),
                                   symbols.LLVMLib(lmath, mathcode_mangler))
# assert not math_library.missing, math_library.missing