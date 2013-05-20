# -*- coding: utf-8 -*-

"""
Math symbols and signatures from the low-level math library.
"""

from __future__ import print_function, division, absolute_import

from os.path import abspath, dirname, join
import ctypes

from numba import *
from . import ltypes, parsesyms, naming
from llvm.core import *

# ______________________________________________________________________
# Required symbols

symbolfile = join(dirname(abspath(__file__)), 'RequiredSymbols.txt')
required_symbols = parsesyms.parse_symbols(open(symbolfile))

typemap = {
    'int': ltypes.integral,
    'float': ltypes.floating,
    'complex': ltypes.complexes
}

# ______________________________________________________________________
# Retrieve symbols

class Lib(object):
    def __init__(self, libm, mangler=naming.mathname, have_symbol=None):
        """
        :param mangler: (name, llvm_type) -> math_name
        """
        self.libm = libm
        self.mangle = mangler
        self._have_symbol = have_symbol

    def have_symbol(self, cname):
        if self._have_symbol is None:
            return self.get_libm_symbol(cname)
        return self._have_symbol(self.libm, cname)

class CtypesLib(Lib):
    def get_libm_symbol(self, cname):
        func = getattr(self.libm, cname, None)
        if func is not None:
            return ctypes.cast(func, ctypes.c_void_p).value

class LLVMLib(Lib):
    def get_libm_symbol(self, cname):
        try:
            return self.libm.get_function_named(cname)
        except llvm.LLVMException:
            return None

def get_symbols(library, libm, required_symbols=required_symbols):
    """
    Populate a dict with runtime addressed of math functions from a given
    ctypes library.

    :param library: math_support.Library to add symbols to
    :param libm: ctypes or LLVM library of math functions
    """
    for symbol in required_symbols:
        types = (symbol.restype,) + symbol.argtypes
        for ltys in zip(*[typemap[ty] for ty in types]):
            sig = ltypes.Signature(ltys[0], ltys[1:])
            if library.get_symbol(symbol.name, sig):
                # Duplicate symbol, e.g. llabs -> labs when
                # sizeof(long) == sizeof(longlong)
                continue

            cname = libm.mangle(symbol.name, sig)
            if libm.have_symbol(cname):
                libm_symbol = libm.get_libm_symbol(cname)
                library.add_symbol(symbol.name, sig, libm_symbol)

    return library