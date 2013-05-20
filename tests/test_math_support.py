# -*- coding: utf-8 -*-
from __future__ import print_function, division, absolute_import

from numba.support.math_support import linking, symbols, ltypes, libs

def test_llvm_linking():
    lib = libs.math_library
    linker = linking.LLVMLinker()
    print(lib)
