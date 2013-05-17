# -*- coding: utf-8 -*-

"""
Support for math as a postpass on LLVM IR.
"""

from __future__ import print_function, division, absolute_import

import os
import abc
import ctypes.util
from os.path import join, dirname
from itertools import imap
import collections

from numba import *
from numba.support import ctypes_support, llvm_support
from numba.pycc import compiler
from numba.support.math_support import symbols

import llvm.core
import numpy.core.umath

root = dirname(__file__)

class Library(object):
    def __init__(self):
        # # { func_name : { return_type, argtype) : link_obj } }
        self.symbols = collections.defaultdict(dict)
        self.missing = []

    def add_symbol(self, name, restype, argtype, val):
        args = str(restype), str(argtype) # types don't hash properly yet
        assert args not in self.symbols[name], (args, self.symbols)
        self.symbols[name][args] = val

    def get_symbol(self, name, restype, argtype):
        return self.symbols.get(name, {}).get((str(restype), str(argtype)))

class LLVMLibrary(Library):
    def __init__(self, module):
        super(LLVMLibrary, self).__init__()
        self.module = module

# ______________________________________________________________________
# openlibm

# print("---------- OPENLIBM -----------")
symbol_data = open(os.path.join(os.path.dirname(__file__), "Symbol.map")).read()
openlibm_symbols = set(word.rstrip(';') for word in symbol_data.split())
openlibm = ctypes.CDLL(ctypes.util.find_library("openlibm"))
olm_have_sym = lambda libm, cname: cname in openlibm_symbols
openlibm_library = symbols.get_symbols(
    Library(), symbols.CtypesLib(openlibm, have_symbol=olm_have_sym))

# ______________________________________________________________________
# NumPy umath

# print("---------- umath -----------")
umath = ctypes.CDLL(numpy.core.umath.__file__)
umath_mangler = lambda name, ty: 'npy_' + symbols.unary_math_suffix(name, ty)
umath_library = symbols.get_symbols(
    Library(), symbols.CtypesLib(umath, mangler=umath_mangler))

# ______________________________________________________________________
# System's libmath

# print("---------- libm -----------")
libm = ctypes.CDLL(ctypes.util.find_library("m"))
libm_library = symbols.get_symbols(Library(), symbols.CtypesLib(libm))

# ______________________________________________________________________

# print("---------- mathcode -----------")
def mathcode_mangler(name, ty):
    if name == 'abs':
        absname = symbols.absname(ty)
        if ty.kind == llvm.core.TYPE_INTEGER:
            return absname # abs(), labs(), llabs()
        elif ty.kind in symbols.float_kinds:
            return 'npy_' + absname
        else:
            return 'nc_' + absname
    elif ty.kind == llvm.core.TYPE_STRUCT:
        return 'nc_' + symbols.unary_math_suffix(name, ty.elements[0])
    else:
        return umath_mangler(name, ty)

dylib = 'mathcode' + compiler.find_shared_ending()
llvmmath = ctypes.CDLL(join(root, 'mathcode', dylib))
llvm_library = symbols.get_symbols(
    Library(), symbols.CtypesLib(llvmmath, mathcode_mangler))

# Load llvmmath as bitcode
bc = join(root, 'mathcode', 'mathcode.s')
lmath = llvm.core.Module.from_assembly(open(bc))
math_library = symbols.get_symbols(LLVMLibrary(lmath),
                                   symbols.LLVMLib(lmath, mathcode_mangler))

# ______________________________________________________________________

def link_pointer(engine, module, library, lfunc, ptr):
    engine.add_global_mapping(lfunc, ptr)

def link_llvm_asm(engine, module, library, lfunc_src, lfunc_dst):
    module.link_in(library.module)
    lfunc_dst = module.get_function_named(lfunc_dst.name)
    v = lfunc_src._ptr
    v.replaceAllUsesWith(lfunc_dst._ptr)

def link_llvm_math_intrinsics(engine, module, library, link):
    """
    Add a runtime address for all global functions named numba.math.*
    """
    # find all known math intrinsics and implement them.
    for lfunc in module.functions:
        if lfunc.name.startswith("numba.math."):
            _, _, name = lfunc.name.rpartition('.')

            restype = lfunc.type.pointee.return_type
            argtype = lfunc.type.pointee.args[0]

            linkarg = library.get_symbol(name, restype, argtype)
            link(engine, module, library, lfunc, linkarg)
            # print("adding", lfunc, linkarg)