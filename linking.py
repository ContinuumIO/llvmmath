# -*- coding: utf-8 -*-

"""
Support for math as a postpass on LLVM IR.
"""

from __future__ import print_function, division, absolute_import

from . import ltypes

import llvm.core as lc
import llvm.passes as lp
import llvm.ee as le
from llvmpy.api import llvm

llvm_context = llvm.getGlobalContext()

def _link_complex(engine, module, library, lfunc_src, lfunc_dst):
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
            # Arguments passed by reference
            newargs = [builder.CreateBitCast(a, ty)
                           for a, ty in zip(args, argtypes)]
            newcall = builder.CreateCall(ldst, newargs)
            callinst.replaceAllUsesWith(newcall)
            callinst.eraseFromParent()

    assert not lsrc.list_use(), map(str, lsrc.list_use())
    lsrc.eraseFromParent()

def make_complex_wrapper(module, lfunc_src, lfunc_dst):
    """
    Create function wrapper for complex math call:

        Create wrapper '{f,f} wrapsin({f,f} arg)' that calls
        'void sin({f,f}* arg, {f,f}* out)'
    """
    dst_fty = lfunc_dst.type.pointee
    dst_argtys = dst_fty.args[:-1]
    dst_retty = dst_fty.args[-1]

    fty = lfunc_src.type.pointee
    name = 'llvmmath.complexwrapper.%s' % (lfunc_src.name,)
    lfunc = module.add_function(fty, name)

    bb = lfunc.append_basic_block('entry')
    b = lc.Builder.new(bb)

    ret = b.alloca(fty.return_type, 'result')

    newargs = []
    for arg, dst_argty in zip(lfunc.args, dst_argtys):
        dstarg = b.alloca(arg.type, 'arg')
        b.store(arg, dstarg)
        newargs.append(b.bitcast(dstarg, dst_argty))
    print(".........", ret, dst_retty)
    b.call(lfunc_dst, newargs + [b.bitcast(ret, dst_retty)])
    print("...")
    b.ret(b.load(ret))

    return lfunc

# ______________________________________________________________________
# Library linkers

class Linker(object):
    "Link math functions into a destination module"

    def setup(self, engine, module, library):
        "Link math functions from the library into the destination module"

    def link(self, engine, module, library, lfunc_src, lfunc_dst):
        "Replace unbound math function lfunc_src with math function lfunc_dst"

    def optimize(self, engine, module, library):
        "Optimize after linking (inlining, DCE, etc)"

class LLVMLinker(Linker):

    def setup(self, engine, module, library):
        module.link_in(library.module, preserve=True)

    def link(self, engine, module, library, lfunc_src, lfunc_dst):
        "Link the math to an LLVM math library"
        lfunc_dst = module.get_function_named(lfunc_dst.name)
        v = lfunc_src._ptr
        if lfunc_src.type != lfunc_dst.type:
            if lfunc_dst.name.startswith('nc_'):
                # _link_complex(engine, module, library, lfunc_src, lfunc_dst)
                lfunc_dst = make_complex_wrapper(module, lfunc_src, lfunc_dst)
            else:
                raise ValueError("Incorrect signature for %s (got '%s', need '%s')" % (
                                    lfunc_src.name, lfunc_dst.type, lfunc_src.type))

        assert lfunc_dst.type == lfunc_src.type, (str(lfunc_dst.type), str(lfunc_src.type))
        v.replaceAllUsesWith(lfunc_dst._ptr)

    def optimize(self, engine, module, library):
        "Try to eliminate unused functions"
        # for lfunc_math in library.module.functions:
        #     lfunc = module.get_function_named(lfunc_math.name)
        #     lfunc.linkage = lc.LINKAGE_INTERNAL
        #
        # fpm = lp.PassManager.new()
        # fpm.add(lp.PASS_GLOBALDCE)
        # fpm.run(module)
        return

class ExternalLibraryLinker(Linker):

    def link(self, engine, module, library, lfunc, ptr):
        "Link the math by adding pointers to functions in external code"
        engine.add_global_mapping(lfunc, ptr)

# ______________________________________________________________________

def link_llvm_math_intrinsics(engine, module, library, linker, replacements):
    """
    Link all abstract math calls by adding a runtime address or by replacing
    callsites with a different LLVM function.

    :param library: math_support.Library of math symbols
    :param link: link function (e.g. link_pointer)
    :param replacements: { abstract_math_name -> math_name }
    """
    linker.setup(engine, module, library)

    # find all known math intrinsics and implement them.
    for lfunc in module.functions:
        if lfunc.name in replacements:
            name = replacements[lfunc.name]
            argtypes = lfunc.type.pointee.args
            restype = lfunc.type.pointee.return_type

            # Complex numbers are passed by reference
            if restype.kind == lc.TYPE_VOID:
                assert len(argtypes) == 2
                restype = argtypes[1].pointee
                argtypes = [argtypes[0].pointee]

            sig = ltypes.Signature(restype, argtypes)
            linkarg = library.get_symbol(name, sig)
            assert linkarg, (name, sig, library.symbols[name])
            linker.link(engine, module, library, lfunc, linkarg)
            del lfunc # this is dead now, don't touch

    linker.optimize(engine, module, library)