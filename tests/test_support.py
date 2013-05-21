# -*- coding: utf-8 -*-

"""
Some test helpers.
"""

from __future__ import print_function, division, absolute_import

import types
import ctypes
import collections

from .. import llvm_support

import llvm
import llvm.core as lc
import llvm.passes as lp
import llvm.ee as le

LLVMContext = collections.namedtuple("LLVMContext", "engine module pm")

def make_llvm_context(name="mymodule"):
    "Return an LLVM context (engine, module, passmanager)"
    module = lc.Module.new("numba_executable_module")
    features = '-avx'
    tm = le.TargetMachine.new(opt=3, cm=le.CM_JITDEFAULT, features=features)
    engine = le.EngineBuilder.new(module).create(tm)
    passmanagers = lp.build_pass_managers(tm, opt=3,
                                          inline_threshold=1000,
                                          fpm=False)
    return LLVMContext(engine, module, passmanagers.pm)

def make_mod(ctx):
    m = types.ModuleType('testmod')
    llvm_support.wrap_llvm_module(ctx.module, ctx.engine, m)
    return m

#===------------------------------------------------------------------===
# Call complex functions
#===------------------------------------------------------------------===

def build_complex_args(f, *inputs):
    c_args = []
    for c_argty, input in zip(f.argtypes, inputs):
        c_args.append(c_argty(input.real, input.imag))
    return c_args

def call_complex_byval(f, *inputs):
    "Call unary complex function by value, e.g. complex func(complex)"
    c_args = build_complex_args(f, *inputs)
    c_result = f(*c_args)
    return complex(c_result.e0, c_result.e1)

def call_complex_byref(f, input):
    """
    Call unary complex function by reference, e.g.
    void sin(complex *, complex *)
    """
    if f.restype is not None:
        return call_complex_byval_return(f, input)
    c_argty = f.argtypes[0]._type_ # get base type from pointer argtype
    c_resty = f.argtypes[1]._type_

    c_result = c_resty(0)
    c_input = c_argty(input.real, input.imag)
    c_input_p, c_result_p = ctypes.pointer(c_input), ctypes.pointer(c_result)
    f(c_input_p, c_result_p)

    if issubclass(c_resty, ctypes.Structure):
        return complex(c_result.e0, c_result.e1)
    return c_resty

def call_complex_byval_return(f, input):
    "Call something like float abs(complex)"
    c_argty = f.argtypes[0]._type_ # get base type from pointer argtype
    c_input = c_argty(input.real, input.imag)
    c_result = f(ctypes.pointer(c_input))
    return c_result

#===------------------------------------------------------------------===
# Function wrapping
#===------------------------------------------------------------------===

def _have_func(mod, name):
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
    assert not _have_func(mod, name)

    argtys = map(lc.Type.pointer, wfty.args + [wfty.return_type])
    fty = lc.Type.function(lc.Type.void(), argtys)

    f = mod.add_function(fty, name)
    bb = f.append_basic_block('entry')
    b = lc.Builder.new(bb)

    ret = b.call(wrapped, map(b.load, f.args[:-1]))
    b.store(ret, f.args[-1])
    b.ret_void()
    return f

def create_byval_wrapper(wrapped, name):
    """
    Create a simple function wrapper for testing.
    """
    mod = wrapped.module
    assert not _have_func(mod, name)

    f = mod.add_function(wrapped.type.pointee, name)
    bb = f.append_basic_block('entry')
    b = lc.Builder.new(bb)
    ret = b.call(wrapped, f.args)
    b.ret(ret)
    return f
