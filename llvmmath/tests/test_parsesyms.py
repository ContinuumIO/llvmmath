# -*- coding: utf-8 -*-
from __future__ import print_function, division, absolute_import

from io import StringIO

from llvmmath import parsesyms
from llvmmath.parsesyms import Symbol
from llvmmath.tests.support import test

testfuncs = u"""
float sin(float)
complex pow(complex, int)
int abs(int)
float abs(float)
float abs(complex)
"""

testcomments = u"""
# comment1
#   comment2
    # comment3
float sin(float) # comment4
"""

symdict = lambda syms: dict((sym.name, sym) for sym in syms)

@test
def test_parsefuncs():
    syms = symdict(parsesyms.parse_symbols(StringIO(testfuncs)))
    assert syms['sin'].name == 'sin'
    assert syms['sin'].restype == 'float'
    assert syms['sin'].argtypes == ('float',)

    assert syms['pow'].argtypes == ('complex', 'int')

@test
def test_duplicates():
    syms = parsesyms.parse_symbols(StringIO(testfuncs))
    collected = []
    for sym in syms:
        if sym.name == 'abs':
            collected.append(sym)

    assert len(collected) == 3

    expected = set([Symbol('abs', 'int', ('int',)),
                    Symbol('abs', 'float', ('float',)),
                    Symbol('abs', 'float', ('complex',))])

    assert set(collected) == expected

@test
def test_comments():
    syms = symdict(parsesyms.parse_symbols(StringIO(testcomments)))
    assert len(syms) == 1
    assert syms['sin'].name == 'sin'
    assert syms['sin'].restype == 'float'
    assert syms['sin'].argtypes == ('float',)
