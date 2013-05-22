__version__ = '0.1'

import logging.config

logging.basicConfig()
# logging.config.fileConfig('logging.conf')

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

from testrunner import test
from build import have_llvm_asm
from libs import get_default_math_lib, get_mathlib_so, get_mathlib_bc
from libs import get_libm, get_openlibm