# -*- coding: utf-8 -*-
from __future__ import print_function, division, absolute_import

import ctypes
import collections
from . import build

import numpy as np
from llvm.core import *
import llvm.ee

from . import have_llvm_asm

#===------------------------------------------------------------------===
# long double
#===------------------------------------------------------------------===

def guess_longdouble_type():
    """
    Do as best we can to get a long double representation compatible with numpy
    """
    is_ppc, is_x86 = get_target_triple()

    l_80 = Type.x86_fp80()
    l_128 = Type.fp128()
    l_ppc = Type.ppc_fp128()

    if hasattr(np, 'float128'):
        itemsize = np.dtype(np.float128).itemsize
    else:
        itemsize = ctypes.sizeof(ctypes.c_longdouble)

    if hasattr(np, 'float96'):
        return l_80
    elif itemsize == 16:
        if is_ppc:
            return l_ppc
        else:
            assert is_x86
            return l_80
            # return l_128
    else:
        assert itemsize == 8
        return Type.double()

def get_target_triple():
    target_machine = llvm.ee.TargetMachine.new()
    is_ppc = target_machine.target_name.startswith("ppc")
    is_x86 = target_machine.target_name.startswith("x86")
    return is_ppc, is_x86

def get_longdouble_from_llvm():
    "Get the long double type from npy_sinl"
    mathcode_asm = build.load_llvm_asm()
    sinl = mathcode_asm.get_function_named('npy_sinl')
    l_longdouble = sinl.type.pointee.args[0]
    return l_longdouble

def get_longdouble_type():
    if have_llvm_asm():
        return get_longdouble_from_llvm()
    else:
        return guess_longdouble_type()

#===------------------------------------------------------------------===
# Types
#===------------------------------------------------------------------===

l_int        = Type.int(ctypes.sizeof(ctypes.c_int) * 8)
l_long       = Type.int(ctypes.sizeof(ctypes.c_long) * 8)
l_longlong   = Type.int(ctypes.sizeof(ctypes.c_longlong) * 8)
l_float      = Type.float()
l_double     = Type.double()
l_longdouble = get_longdouble_type()
l_complex64  = Type.struct([l_float, l_float])
l_complex128 = Type.struct([l_double, l_double])
l_complex256 = Type.struct([l_longdouble, l_longdouble])

integral  = (l_int, l_long, l_longlong)
floating  = (l_float, l_double, l_longdouble)
complexes = (l_complex64, l_complex128, l_complex256)

all_types = integral + floating + complexes

# ty = lambda name: mathcode_asm.get_global_variable_named(name).type
# complexes = [ty('nc_if'), ty('nc_i'), ty('nc_il')]

complexes_by_ref = [Type.pointer(ct) for ct in complexes]

# ______________________________________________________________________

float_kinds = (TYPE_FLOAT, TYPE_DOUBLE, TYPE_X86_FP80, TYPE_FP128, TYPE_PPC_FP128)
is_float = lambda lty: lty.kind in float_kinds

# ______________________________________________________________________

def strsig(restype, argtypes):
    # types may not hash properly, use the str
    return str(restype), tuple(map(str, argtypes))

Signature = collections.namedtuple('Signature', ['restype', 'argtypes'])
Signature.__hash__ = lambda self: hash(strsig(*self))
Signature.__eq__ = lambda self, other: strsig(*self) == strsig(*other)
Signature.__neq__ = lambda self, other: strsig(*self) != strsig(*other)
Signature.__repr__ = lambda self: str(strsig(*self))

# ______________________________________________________________________
