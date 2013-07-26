# -*- coding: utf-8 -*-
from __future__ import print_function, division, absolute_import

__version__ = '0.1'

from os.path import dirname, abspath
import unittest
import logging

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.getLogger("llvmpy").setLevel(logging.WARN)

from .build import have_llvm_asm, have_clang
from .libs import get_default_math_lib, get_mathlib_so, get_llvm_mathlib
from .libs import get_libm, get_openlibm

# ______________________________________________________________________
# llvmmath.test()

root = dirname(dirname(abspath(__file__)))
pattern = "test_*.py"

def test(root=root, pattern=pattern):
    """Run tests and return exit status"""
    tests =  unittest.TestLoader().discover(root, pattern=pattern)
    runner = unittest.TextTestRunner()
    result = runner.run(tests)
    return not result.wasSuccessful()