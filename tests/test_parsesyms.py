# -*- coding: utf-8 -*-
from __future__ import print_function, division, absolute_import

from StringIO import StringIO

from .. import parsesyms

testfuncs = """
float sin(float)
complex pow(complex, int)
int abs(int)
"""

testcomments = """
# comment1
#   comment2
    # comment3
float sin(float) # comment4
"""

symdict = lambda syms: dict((sym.name, sym) for sym in syms)

def test_parsefuncs():
    syms = symdict(parsesyms.parse_symbols(StringIO(testfuncs)))
    assert syms['sin'].name == 'sin'
    assert syms['sin'].restype == 'float'
    assert syms['sin'].argtypes == ('float',)

    assert syms['pow'].argtypes == ('complex', 'int')
    assert syms['abs'].restype == 'int'

def test_comments():
    syms = symdict(parsesyms.parse_symbols(StringIO(testcomments)))
    assert len(syms) == 1
    assert syms['sin'].name == 'sin'
    assert syms['sin'].restype == 'float'
    assert syms['sin'].argtypes == ('float',)