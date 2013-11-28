# -*- coding: utf-8 -*-

"""
Support for math as a postpass on LLVM IR.
"""

from __future__ import print_function, division, absolute_import

from . import libs
from . import ltypes
from . import complex_support

import llvm.core as lc
from llvmpy.api import llvm

llvm_context = llvm.getGlobalContext()

#===------------------------------------------------------------------===
# Complex linking
#===------------------------------------------------------------------===

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

# ______________________________________________________________________

def link_complex_llvm(lfunc_dst, lfunc_src):
    """
    Link a complex math function called by value to an LLVM implementation
    taking arguments by reference.

        complex sin(complex) -> complex wrapper_sin(complex)

    where

        complex wrapper_sin(complex arg) {
            complex out; nc_sin(&arg, &out); return out;
        }

    nc_sin needs to have been linked into the module.
    """
    if lfunc_dst.name.startswith('nc_'):
        name = 'llvmmath.complexwrapper.%s' % (lfunc_src.name,)
        lfunc_dst = complex_support.create_val2ref_wrapper(
            lfunc_dst, name, lfunc_src.type.pointee)
        assert (lfunc_dst.module is lfunc_src.module)
        lfunc_dst.linkage = lc.LINKAGE_LINKONCE_ODR
    else:
        raise ValueError(
            "Incorrect signature for %s (got '%s', need '%s')" % (
                lfunc_src.name, lfunc_dst.type, lfunc_src.type))

    lfunc_src._ptr.replaceAllUsesWith(lfunc_dst._ptr)

def link_complex_external(lfunc, module):
    """
    Link a complex math function called by value to an external implementation
    taking arguments by reference. Returns a function declaration for the
    external function, which needs an address assigned (add_global_mapping).

        complex sin(complex) -> complex wrapper_sin(complex)

    where

        complex wrapper_sin(complex arg) {
            complex out; nc_sin(&arg, &out); return out;
        }

    Returns nc_sin, which needs an external address.
    """
    fty = lfunc.type.pointee

    name = 'llvmmath.external.%s' % (lfunc.name,)
    wrapper_name = 'llvmmath.externalwrap.%s' % (lfunc.name,)

    argtys = map(lc.Type.pointer, fty.args + [fty.return_type])
    reffty = lc.Type.function(lc.Type.void(), argtys)
    wrapped = module.add_function(reffty, name)

    lfunc_wrapper = complex_support.create_val2ref_wrapper(
        wrapped, wrapper_name, lfunc.type.pointee)
    lfunc_wrapper.linkage = lc.LINKAGE_LINKONCE_ODR

    lfunc._ptr.replaceAllUsesWith(lfunc_wrapper._ptr)
    return wrapped

#===------------------------------------------------------------------===
# Library linkers
#===------------------------------------------------------------------===

class Linker(object):
    "Link math functions into a destination module"

    def setup(self, engine, module, library):
        "Link math functions from the library into the destination module"

    def link(self, engine, module, library, lfunc_src, lfunc_dst):
        "Replace unbound math function lfunc_src with math function lfunc_dst"

    def optimize(self, engine, module, library):
        "Optimize after linking (inlining, DCE, etc)"

class LLVMLinker(Linker):
    """
    Resolve abstract math calls to calls from mathcode.s and link mathcode.s
    into module.
    """

    def setup(self, engine, module, library):
        module.link_in(library.module, preserve=True)

    def link(self, engine, module, library, lfunc_src, lfunc_dst):
        "Link the math to an LLVM math library"
        lfunc_dst = module.get_function_named(lfunc_dst.name)
        v = lfunc_src._ptr
        if lfunc_src.type != lfunc_dst.type:
            link_complex_llvm(lfunc_dst, lfunc_src)
        else:
            v.replaceAllUsesWith(lfunc_dst._ptr)

    def optimize(self, engine, module, library):
        "Try to eliminate unused functions"
        for lfunc_math in library.module.functions:
            lfunc = module.get_function_named(lfunc_math.name)
            # Don't use 'lfunc.uses', it may break when we have a constant
            # expression as user:  TypeError: Downcast from llvm::User to
            # llvm::ConstantExpr is not supported
            if not lfunc._ptr.list_use():
                lfunc.delete()
            elif not lfunc.is_declaration:
                lfunc.linkage = lc.LINKAGE_LINKONCE_ODR

        for global_val in library.module.global_variables:
            gv = module.get_global_variable_named(global_val.name)
            gv.linkage = lc.LINKAGE_LINKONCE_ODR

        # fpm = lp.PassManager.new()
        # fpm.add(lp.PASS_GLOBALDCE)
        # fpm.run(module)
        return

class ExternalLibraryLinker(Linker):

    def link(self, engine, module, library, lfunc, ptr):
        "Link the math by adding pointers to functions in external code"
        is_complex = lfunc.args[0].type.kind == lc.TYPE_STRUCT
        if is_complex:
            lfunc = link_complex_external(lfunc, module)

        engine.add_global_mapping(lfunc, ptr)

#===------------------------------------------------------------------===
# Linking
#===------------------------------------------------------------------===

def get_linker(lib):
    "Get linker for the given math library"
    if isinstance(lib, libs.LLVMLibrary):
        return LLVMLinker()
    else:
        return ExternalLibraryLinker()

def link_llvm_math_intrinsics(engine, module, library, linker, replacements):
    """
    Link all abstract math calls by adding a runtime address or by replacing
    callsites with a different LLVM function.

    :param engine: llvm execution engine
    :param module: llvm module containing math calls
    :param library: ``llvmmath.math_support.Library`` of math symbols
    :param linker: linker that can link the math library
    :type linker: ``llvmmath.linking.Linker``
    :param replacements: { abstract_math_name -> math_name }
    :type replacements: dict of str -> str
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

            # See whether our symbol is available
            if linkarg is None:
                raise LookupError(
                    "Symbol %s with signature %s not available, "
                    "we only have %s" % (name, sig, library.symbols[name]))

            linker.link(engine, module, library, lfunc, linkarg)
            del lfunc # this is dead now, don't touch

    linker.optimize(engine, module, library)
