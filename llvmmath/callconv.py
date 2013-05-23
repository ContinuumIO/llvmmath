# -*- coding: utf-8 -*-

"""
Handle calling convention for math function. A calling convention maps
Signatures to Signatures.
"""

from __future__ import print_function, division, absolute_import
from . import ltypes

import llvm.core as lc

def convention_cbyref(signature):
    "Pass complex numbers by reference. The return value is the last argument"
    args = []
    for arg in signature.argtypes:
        if arg.kind == lc.TYPE_STRUCT:
            arg = lc.Type.pointer(arg)
        args.append(arg)

    if signature.restype.kind == lc.TYPE_STRUCT:
        args.append(lc.Type.pointer(signature.restype))
        restype = lc.Type.void()
    else:
        restype = signature.restype

    return ltypes.Signature(restype, args)