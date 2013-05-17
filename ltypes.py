# -*- coding: utf-8 -*-
from __future__ import print_function, division, absolute_import

import ctypes
from . import build
from llvm.core import Type

mathcode_asm = build.load_llvm_asm()
sinl = mathcode_asm.get_function_named('npy_sinl')

l_int        = Type.int(ctypes.sizeof(ctypes.c_int) * 8)
l_long       = Type.int(ctypes.sizeof(ctypes.c_long) * 8)
l_longlong   = Type.int(ctypes.sizeof(ctypes.c_longlong) * 8)
l_float      = Type.float()
l_double     = Type.double()
l_longdouble = sinl.type.pointee.args[0]
l_complex64  = Type.struct([l_float, l_float])
l_complex128 = Type.struct([l_double, l_double])
l_complex256 = Type.struct([l_longdouble, l_longdouble])

integral  = [l_int, l_long, l_longlong]
floating  = [l_float, l_double, l_longdouble]
complexes = [l_complex64, l_complex128, l_complex256]

# ty = lambda name: mathcode_asm.get_global_variable_named(name).type
# complexes = [ty('nc_if'), ty('nc_i'), ty('nc_il')]

complexes_by_ref = [Type.pointer(ct) for ct in complexes]