#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function, division, absolute_import

from os.path import abspath, dirname, join
import sys
import llvmmath

kwds = {}
if len(sys.argv) > 1:
    kwds["pattern"] = sys.argv[1]

root = dirname(abspath(llvmmath.__file__))
sys.exit(llvmmath.test(root, **kwds))