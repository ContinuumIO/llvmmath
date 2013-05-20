# -*- coding: utf-8 -*-
from __future__ import print_function, division, absolute_import

from numba.support.math_support import math_support, symbols, ltypes, libs

def test_llvm_linking():
    lib = libs.math_library
    linker = math_support.LLVMLinker()
    print(lib)
