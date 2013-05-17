# -*- coding: utf-8 -*-

"""
Support for math as a postpass on LLVM IR.
"""

from __future__ import print_function, division, absolute_import

def link_pointer(engine, module, library, lfunc, ptr):
    engine.add_global_mapping(lfunc, ptr)

def link_llvm_asm(engine, module, library, lfunc_src, lfunc_dst):
    module.link_in(library.module)
    lfunc_dst = module.get_function_named(lfunc_dst.name)
    v = lfunc_src._ptr
    if lfunc_src.type != lfunc_dst.type:
        raise ValueError("Incorrect signature for %s (got '%s', need '%s')" % (
                            lfunc_src.name, lfunc_dst.type, lfunc_src.type))
    v.replaceAllUsesWith(lfunc_dst._ptr)

def link_llvm_math_intrinsics(engine, module, library, link):
    """
    Add a runtime address for all global functions named numba.math.*
    """
    # find all known math intrinsics and implement them.
    for lfunc in module.functions:
        if lfunc.name.startswith("numba.math."):
            _, _, name = lfunc.name.rpartition('.')

            restype = lfunc.type.pointee.return_type
            argtype = lfunc.type.pointee.args[0]

            linkarg = library.get_symbol(name, restype, argtype)
            link(engine, module, library, lfunc, linkarg)
            # print("adding", lfunc, linkarg)