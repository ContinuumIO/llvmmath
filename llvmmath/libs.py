# -*- coding: utf-8 -*-

"""
Support for math as a postpass on LLVM IR.
"""

from __future__ import print_function, division, absolute_import

import os
import glob
import ctypes.util
from os.path import join, dirname, exists
import collections

from . import build, ltypes, naming, llvm_support, callconv
from .utils import cached
from .symbols import CtypesMath, LLVMMath, get_symbols

import llvm.core
import llvm.ee
import numpy.core.umath

root = dirname(__file__)

# ______________________________________________________________________

class Library(object):
    def __init__(self, module, calling_conv):
        self.module = module # library module (ctypes of llvm module)
        self.calling_convention = calling_conv # Signature -> Signature

        # # { func_name : { signature : link_obj } }
        self.symbols = collections.defaultdict(dict)
        self.missing = [] # (name, cname, sig)

    def add_symbol(self, name, sig, val):
        assert sig not in self.symbols[name], (sig, self.symbols)
        self.symbols[name][sig] = val

    def get_symbol(self, name, signature):
        return self.symbols.get(name, {}).get(signature)

    def format_linkable(self, linkable):
        return str(linkable)

    def __str__(self):
        result = []
        for symbol, d in sorted(self.symbols.iteritems()):
            for (rty, argtys), linkable in d.iteritems():
                linkable_str = self.format_linkable(linkable)
                result.append("%s %s(%s): %s" % (
                    rty, symbol, ", ".join(map(str, argtys)), linkable_str))

        sep = "\n    "
        return "Library(%s%s)" % (sep, sep.join(result))

class CtypesLibrary(Library):
    def format_linkable(self, linkable):
        return hex(linkable)

    def get_ctypes_symbol(self, name, signature):
        ptr = self.get_symbol(name, signature)
        assert ptr is not None, (name, signature)
        native_sig = self.calling_convention(signature)
        to_ctypes = llvm_support.map_llvm_to_ctypes

        sym = ctypes.cast(ptr, ctypes.CFUNCTYPE(None))
        sym.restype = to_ctypes(native_sig.restype)
        sym.argtypes = list(map(to_ctypes, native_sig.argtypes))
        return sym

class LLVMLibrary(Library):
    def format_linkable(self, linkable):
        return linkable.name

    def get_ctypes_symbol(self, name, signature):
        lfunc = self.get_symbol(name, signature)
        assert lfunc is not None and lfunc.module
        engine = llvm.ee.ExecutionEngine.new(lfunc.module)
        return llvm_support.get_ctypes_wrapper(lfunc, engine)

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

libmap = { CtypesMath: CtypesLibrary, LLVMMath: LLVMLibrary }

def get_syms(mathlib, libmap=libmap, cc=callconv.convention_cbyref):
    Library = libmap[type(mathlib)]
    library = Library(mathlib.libm, cc)
    return get_symbols(library, mathlib)

# ______________________________________________________________________

@cached
def get_libm():
    "Get a math library from the system's libm"
    libm = ctypes.CDLL(ctypes.util.find_library("m"))
    return get_syms(CtypesMath(libm))

@cached
def get_umath():
    "Load numpy's umath as a math library"
    umath = ctypes.CDLL(numpy.core.umath.__file__)
    return get_syms(CtypesMath(umath, mangler=umath_mangler))

@cached
def get_openlibm():
    "Load openlibm from its shared library"
    symbol_data = open(join(dirname(__file__), "Symbol.map")).read()
    openlibm_symbols = set(word.rstrip(';') for word in symbol_data.split())
    openlibm = ctypes.CDLL(ctypes.util.find_library("openlibm"))

    have_sym = lambda libm, cname: cname in openlibm_symbols
    return get_syms(CtypesMath(openlibm, have_symbol=have_sym))

# ______________________________________________________________________

@cached
def get_mathlib_as_ctypes():
    "Get the math library as a ctypes CDLL"
    so = build.find_shared_ending()
    pattern = join(root, 'mathcode', 'mathcode*' + so)
    dylibs = glob.glob(pattern)
    if len(dylibs) != 1 or not exists(dylibs[0]):
        files = os.listdir(join(root, 'mathcode'))
        raise OSError("File not found: %s. Files: %s" % (pattern, files))

    return ctypes.CDLL(dylibs[0])

@cached
def get_mathlib_so():
    "Load the math from mathcode/ from a shared library"
    llvmmath = get_mathlib_as_ctypes()
    return get_syms(CtypesMath(llvmmath, mathcode_mangler))

@cached
def get_llvm_mathlib():
    "Load the math from mathcode/ from clang-compiled llvm assembly"
    lmath = build.load_llvm_asm()
    return get_syms(LLVMMath(lmath, mathcode_mangler))

# ______________________________________________________________________
# Default library

def get_default_math_lib():
    "Get the default math library implementation"
    if build.have_llvm_asm():
        return get_llvm_mathlib()
    else:
        return get_mathlib_so()
