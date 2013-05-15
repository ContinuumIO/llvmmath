# -*- coding: utf-8 -*-
from __future__ import print_function, division, absolute_import

from numba.support.math_support import math_support

library = math_support.use_openlibm()
print(library)