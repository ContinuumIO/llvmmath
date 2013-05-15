# -*- coding: utf-8 -*-
from __future__ import print_function, division, absolute_import

from numba.support.math_support import math_support, symbols

# library = symbols.get_symbols(math_support.openlibm)

library = symbols.get_symbols(math_support.umath, math_support.umath_mangler)
print(library)