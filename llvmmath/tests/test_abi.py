# -*- coding: utf-8 -*-
from __future__ import print_function, division, absolute_import

from functools import partial

from llvmmath import ltypes
from llvmmath.tests import support
from llvmmath.tests.support import test

from llvm.core import *

# @test
# def test_complex_abi_byval():
#     run_byval(ltypes.l_complex64)  # This one always breaks
#     run_byval(ltypes.l_complex128) # This one breaks on some platforms
#     run_byval(ltypes.l_complex256) # This one always breaks

@test
def test_complex_abi_byref():
    run_byref(ltypes.l_complex64)
    run_byref(ltypes.l_complex128)
    run_byref(ltypes.l_complex256)

# ______________________________________________________________________

def run(wrap, call_wrapped, ty):
    engine, mod, pm = ctx = support.make_llvm_context()
    double_func = make_double_func(mod, ty)
    wrap(double_func, 'wrapper')

    pymod = support.make_mod(ctx)
    result = call_wrapped(pymod.wrapper, 5+6j)
    assert result == 10+12j, result

run_byval = partial(run, support.create_byval_wrapper,
                    support.call_complex_byval)
run_byref = partial(run, support.create_byref_wrapper,
                    support.call_complex_byref)

# ______________________________________________________________________

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