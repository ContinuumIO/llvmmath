# -*- coding: utf-8 -*-

"""
Support for creating wrappers
"""

from __future__ import print_function, division, absolute_import

from . import ltypes

import llvm
import llvm.core as lc

#===------------------------------------------------------------------===
# Printing
#===------------------------------------------------------------------===

def print_complex(mod, builder, *complex_vals):
    try:
        mod.get_global_variable_named('fmtstring')
    except llvm.LLVMException:
        lconst_str = lc.Constant.stringz("complex: %f %f\n")
        ret_val = mod.add_global_variable(lconst_str.type, 'fmtstring')
        ret_val.linkage = llvm.core.LINKAGE_LINKONCE_ODR
        ret_val.initializer = lconst_str
        ret_val.is_global_constant = True

    fmtstring = mod.get_global_variable_named('fmtstring')

    for complex_val in complex_vals:
        real = builder.extract_value(complex_val, 0)
        imag = builder.extract_value(complex_val, 1)

        str_ty = lc.Type.pointer(lc.Type.int(1))
        printf_ty = lc.Type.function(
            ltypes.l_int, [str_ty], var_arg=True)
        printf = mod.get_or_insert_function(printf_ty, 'printf')
        builder.call(printf, [builder.bitcast(fmtstring, str_ty), real, imag])

#===------------------------------------------------------------------===
# Function wrapping
#===------------------------------------------------------------------===

def have_lfunc(mod, name):
    try:
        mod.get_function_named(name)
        return True
    except llvm.LLVMException:
        return False

def create_byref_wrapper(wrapped, name):
    """
    Create an llvm function wrapper that takes arguments by reference, since
    LLVM and C disagree on the ABI for struct (and long double?) types.
    """
    mod = wrapped.module
    wfty = wrapped.type.pointee
    assert not have_lfunc(mod, name)

    argtys = map(lc.Type.pointer, wfty.args + [wfty.return_type])
    fty = lc.Type.function(lc.Type.void(), argtys)

    f = mod.add_function(fty, name)
    bb = f.append_basic_block('entry')
    b = lc.Builder.new(bb)

    args = list(map(b.load, f.args[:-1]))
    # print_complex(mod, b, *args)
    ret = b.call(wrapped, args)
    b.store(ret, f.args[-1])
    b.ret_void()
    return f