# -*- coding: utf-8 -*-
from __future__ import print_function, division, absolute_import

__version__ = '0.1'

import logging.config

logging.basicConfig()
# logging.config.fileConfig('logging.conf')

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

logging.getLogger("llvmpy").setLevel(logging.WARN)

from .testrunner import test
from .build import have_llvm_asm, have_clang
from .libs import get_default_math_lib, get_mathlib_so, get_llvm_mathlib
from .libs import get_libm, get_openlibm
