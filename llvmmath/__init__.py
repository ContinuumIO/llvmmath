# -*- coding: utf-8 -*-
from __future__ import print_function, division, absolute_import

__version__ = '0.1.1'

from os.path import dirname, abspath
import logging
import unittest
import fnmatch

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.getLogger("llvmpy").setLevel(logging.WARN)

from .build import have_llvm_asm, have_clang
from .libs import get_default_math_lib, get_mathlib_so, get_llvm_mathlib
from .libs import get_libm, get_openlibm

# ______________________________________________________________________
# llvmmath.test()

pattern = "*test_*"

def test(pattern=pattern):
    """Run tests and return exit status"""
    # We can't use unittest's discover feature, since it's new in 2.7
    # We can't have a dependency on unittest2
    from llvmmath.tests import (test_abi, test_build, test_libs, test_linking,
                                test_parsesyms, test_symbols)

    # Find and load tests
    tests = []
    loader = unittest.TestLoader()
    for module in (test_abi, test_build, test_libs, test_linking,
                   test_parsesyms, test_symbols):
        print(module.__name__, pattern)
        if fnmatch.fnmatch(module.__name__, pattern):
            tests.extend(loader.loadTestsFromModule(module))

    runner = unittest.TextTestRunner()
    result = runner.run(unittest.TestSuite(tests))
    return not result.wasSuccessful()
