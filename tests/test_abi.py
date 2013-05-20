# -*- coding: utf-8 -*-
from __future__ import print_function, division, absolute_import

import types
from functools import partial

from .. import ltypes, llvm_support
from . import test_support

from llvm.core import *
from llvm.ee import GenericValue

def test_complex_abi():
    # run_test(ltypes.l_complex64)  # This one breaks
    run_test(ltypes.l_complex128)
    # run_test(ltypes.l_complex256) # This one breaks

def run_test(ty):
    engine, mod, pm = test_support.make_llvm_context()

    lfunc = make_func(mod, ty)
    print(mod)

    pymod = types.ModuleType('wrapper')
    llvm_support.wrap_llvm_function(lfunc, engine, pymod)
    c_argty = pymod.wrapper.argtypes[0]
    arg = c_argty(5.0, 6.0)
    assert (arg.e0, arg.e1) == (5.0, 6.0)
    result = pymod.wrapper(arg)
    result_tup = (result.e0, result.e1)
    assert result_tup == (10.0, 12.0), result_tup

    # real = partial(GenericValue.real, ty.elements[0])
    # struct = GenericValue.struct
    # result = engine.run_function(lfunc, [struct([real(1.0), real(2.0)])])
    # print(result)

# ______________________________________________________________________

def make_func(mod, ty):
    "def wrapper(x): return double(x)"
    double = make_double_func(mod, ty)
    lfunc, builder = make_complex_func(mod, ty, 'wrapper')
    result = builder.call(double, [lfunc.args[0]])
    builder.ret(result)
    return lfunc

def make_double_func(mod, ty):
    "def double(x): return complex(x.real + x.real, x.imag + x.imag)"
    lfunc, builder = make_complex_func(mod, ty, 'double')
    real = builder.extract_value(lfunc.args[0], 0)
    imag = builder.extract_value(lfunc.args[0], 1)
    real = builder.fadd(real, real)
    imag = builder.fadd(imag, imag)
    ret = builder.insert_value(lfunc.args[0], real, 0)
    ret = builder.insert_value(ret, imag, 1)
    builder.ret(ret)
    return lfunc

# ______________________________________________________________________

def make_complex_func(mod, ty, name):
    f = mod.add_function(Type.function(ty, [ty]), name)
    bb = f.append_basic_block('entry')
    b = Builder.new(bb)
    return f, b