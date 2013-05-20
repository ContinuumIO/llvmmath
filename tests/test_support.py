# -*- coding: utf-8 -*-
from __future__ import print_function, division, absolute_import

import ctypes
import collections

import llvm.core as lc
import llvm.passes as lp
import llvm.ee as le

LLVMContext = collections.namedtuple("LLVMContext", "engine module pm")

def make_llvm_context(name="mymodule"):
    module = lc.Module.new("numba_executable_module")
    features = '-avx'
    tm = le.TargetMachine.new(opt=3, cm=le.CM_JITDEFAULT, features=features)
    engine = le.EngineBuilder.new(module).create(tm)
    passmanagers = lp.build_pass_managers(tm, opt=3,
                                          inline_threshold=1000,
                                          fpm=False)
    return LLVMContext(engine, module, passmanagers.pm)

def call_complex_byval(f, input):
    c_argty = f.argtypes[0]
    c_input = c_argty(input.real, input.imag)
    c_result = f(c_input)
    return complex(c_result.e0, c_result.e1)

def call_complex_byref(f, input):
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
