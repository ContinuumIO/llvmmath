# -*- coding: utf-8 -*-
from __future__ import print_function, division, absolute_import

from io import StringIO

from .. import parsesyms, symbols, libs
from .. import ltypes as l

testfuncs = u"""
complex pow(complex, int)
int abs(int)
float abs(float)
float abs(complex)
"""

class MockLib(symbols.MathLib):
    def get_libm_symbol(self, cname):
        return 1

def test_duplicates():
    syms = parsesyms.parse_symbols(StringIO(testfuncs))
    lib = symbols.get_symbols(libs.Library(None, None), MockLib(None), syms)

    assert lib.get_symbol('abs', l.Signature(l.l_int, [l.l_int]))
    assert lib.get_symbol('abs', l.Signature(l.l_float, [l.l_complex64]))
    assert lib.get_symbol('abs', l.Signature(l.l_double, [l.l_complex128]))
    assert lib.get_symbol('abs', l.Signature(l.l_longdouble, [l.l_complex256]))
    assert not lib.get_symbol('abs', l.Signature(l.l_complex64, [l.l_complex64]))
