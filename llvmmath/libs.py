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

from . import symbols, build, ltypes, naming
from .utils import cached

import llvm.core
import numpy.core.umath

root = dirname(__file__)

# ______________________________________________________________________

class Library(object):
    def __init__(self):
        # # { func_name : { signature : link_obj } }
        self.symbols = collections.defaultdict(dict)
        self.missing = [] # (name, cname, sig)

    def add_symbol(self, name, sig, val):
        assert sig not in self.symbols[name], (sig, self.symbols)
        self.symbols[name][sig] = val

    def get_symbol(self, name, signature):
        return self.symbols.get(name, {}).get(signature)

    def format_linkable(self, linkable):
        return hex(linkable)

    def __str__(self):
        result = []
        for symbol, d in sorted(self.symbols.iteritems()):
            for (rty, argtys), linkable in d.iteritems():
                linkable_str = self.format_linkable(linkable)
                result.append("%s %s(%s): %s" % (
                    rty, symbol, ", ".join(map(str, argtys)), linkable_str))

        sep = "\n    "
        return "Library(%s%s)" % (sep, sep.join(result))

class LLVMLibrary(Library):
    def __init__(self, module):
        super(LLVMLibrary, self).__init__()
        self.module = module # LLVM math module

    def format_linkable(self, linkable):
        return linkable.name

#===------------------------------------------------------------------===
# Math symbol manglers
#===------------------------------------------------------------------===

umath_mangler = lambda name, ty: 'npy_' + naming.mathname(name, ty)

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

#===------------------------------------------------------------------===
# Public Interface
#===------------------------------------------------------------------===

@cached
def get_libm():
    "Get a math library from the system's libm"
    libm = ctypes.CDLL(ctypes.util.find_library("m"))
    return symbols.get_symbols(Library(), symbols.CtypesLib(libm))

@cached
def get_umath():
    "Load numpy's umath as a math library"
    umath = ctypes.CDLL(numpy.core.umath.__file__)
    umath_library = symbols.get_symbols(
        Library(), symbols.CtypesLib(umath, mangler=umath_mangler))
    return umath_library

@cached
def get_openlibm():
    "Load openlibm from its shared library"
    symbol_data = open(os.path.join(os.path.dirname(__file__), "Symbol.map")).read()
    openlibm_symbols = set(word.rstrip(';') for word in symbol_data.split())
    openlibm = ctypes.CDLL(ctypes.util.find_library("openlibm"))
    olm_have_sym = lambda libm, cname: cname in openlibm_symbols
    openlibm_library = symbols.get_symbols(
        Library(), symbols.CtypesLib(openlibm, have_symbol=olm_have_sym))
    return openlibm_library

@cached
def get_mathlib_so():
    "Load the math from mathcode/ from a shared library"
    dylib = 'mathcode' + build.find_shared_ending()
    llvmmath = ctypes.CDLL(join(root, 'mathcode', dylib))
    llvm_library = symbols.get_symbols(
        Library(), symbols.CtypesLib(llvmmath, mathcode_mangler))
    return llvm_library

@cached
def get_mathlib_bc():
    "Load the math from mathcode/ from clang-compiled bitcode"
    lmath = build.load_llvm_asm()
    return symbols.get_symbols(LLVMLibrary(lmath),
                               symbols.LLVMLib(lmath, mathcode_mangler))

# ______________________________________________________________________
# Default

def get_default_math_lib():
    "Get the default math library implementation"
    if build.have_llvm_asm():
        return get_mathlib_bc()
    else:
        return get_mathlib_so()