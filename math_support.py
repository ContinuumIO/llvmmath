# -*- coding: utf-8 -*-

"""
Support for math as a postpass on LLVM IR.
"""

from __future__ import print_function, division, absolute_import

import llvm.core as lc
from llvmpy.api import llvm

llvm_context = llvm.getGlobalContext()

def link_pointer(engine, module, library, lfunc, ptr):
    engine.add_global_mapping(lfunc, ptr)

def link_complex(engine, module, library, lfunc_src, lfunc_dst):
    """
    Rewrite
        %r = sin({ double, double}* a)
    to
        %a1 = bitcast { double, double}* a to %struct.npy_cdouble*
        %r = sin(%struct.npy_cdouble* a)
    """
    module, lsrc, ldst = module._ptr, lfunc_src._ptr, lfunc_dst._ptr
    argtypes = [arg.getType() for arg in ldst.getArgumentList()]

    builder = llvm.IRBuilder.new(llvm_context)
    for use in lsrc.list_use():
        if use._downcast(llvm.Instruction).getOpcodeName() == 'call':
            callinst = use._downcast(llvm.CallInst)
            builder.SetInsertPoint(callinst)
            args = [callinst.getOperand(i)
                        for i in range(callinst.getNumOperands())]
            newargs = [builder.CreateBitCast(a, ty)
                           for a, ty in zip(args, argtypes)]
            newcall = builder.CreateCall(ldst, newargs)
            callinst.replaceAllUsesWith(newcall)
            callinst.eraseFromParent()

    assert not lsrc.list_use(), map(str, lsrc.list_use())
    lsrc.eraseFromParent()

def link_llvm_asm(engine, module, library, lfunc_src, lfunc_dst):
    module.link_in(library.module)
    lfunc_dst = module.get_function_named(lfunc_dst.name)
    v = lfunc_src._ptr
    if lfunc_src.type != lfunc_dst.type:
        if lfunc_dst.name.startswith('nc_'):
            link_complex(engine, module, library, lfunc_src, lfunc_dst)
        else:
            print(lfunc_dst.name)
            print (library)
            raise ValueError("Incorrect signature for %s (got '%s', need '%s')" % (
                                lfunc_src.name, lfunc_dst.type, lfunc_src.type))
    else:
        v.replaceAllUsesWith(lfunc_dst._ptr)

# ______________________________________________________________________

def link_llvm_math_intrinsics(engine, module, library, link, replacements):
    """
    Link all abstract math calls by adding a runtime address or by replacing
    callsites with a different LLVM function.

    :param library: math_support.Library of math symbols
    :param link: link function (e.g. link_pointer)
    :param replacements: { abstract_math_name -> math_name }
    """
    # find all known math intrinsics and implement them.
    for lfunc in module.functions:
        if lfunc.name in replacements:
            name = replacements[lfunc.name]
            args = lfunc.type.pointee.args

            restype = lfunc.type.pointee.return_type
            argtype = args[0]

            # Complex numbers are passed by reference
            if restype.kind == lc.TYPE_VOID:
                assert len(args) == 2
                restype = args[1]

            linkarg = library.get_symbol(name, restype, argtype)
            assert linkarg, (name, str(restype), str(argtype), library.symbols[name])
            link(engine, module, library, lfunc, linkarg)
            del lfunc # this is dead now, don't touch
            print("adding", linkarg)

    print(module)
    print("----------------")