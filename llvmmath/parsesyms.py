# -*- coding: utf-8 -*-

"""
Parsing of symbol file the following format:

    float sin(float) # some comment
    complex pow(complex, complex)
"""

from __future__ import print_function, division, absolute_import

import re
import collections

# TODO: Make Pymeta a dependency?

Symbol = collections.namedtuple("Symbol", ['name', 'restype', 'argtypes'])

pattern = r'(\w+)\s+(\w+)\((.*)\)' # float sin(...)
comment = r'\s+#.*$'
ident   = r'\w+'

def match_empty(line):
    assert not line.strip() or line.strip().startswith('#'), line

def parse_symbols(file):
    symbols = []
    for line in file:
        m = re.match(pattern, line)
        if m:
            restype, name, argtypes = m.groups()
            argtypes = [argty.strip() for argty in argtypes.split(",")]
            assert all(re.match(ident, argty) for argty in argtypes)
            symbols.append(Symbol(name, restype, tuple(argtypes)))
            line = line[len(m.group(0)):]

        match_empty(line)

    return symbols
