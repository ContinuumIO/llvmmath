__version__ = '0.1'

from testrunner import test
from build import have_bitcode
from libs import get_default_math_lib, get_mathlib_so, get_mathlib_bc
from libs import get_libm, get_openlibm