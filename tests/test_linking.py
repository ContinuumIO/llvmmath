# -*- coding: utf-8 -*-
from __future__ import print_function, division, absolute_import

import ctypes
import types
from collections import namedtuple
from functools import partial
import math
import cmath

from .. import ltypes, llvm_support, linking, libs
from . import test_support

import numpy as np
from llvm.core import *
from llvm.ee import GenericValue

# ______________________________________________________________________

sinname = 'my_custom_sin'
cosname = 'my.custom.cos'
powname = 'my.special.pow'

namemap = {
    sinname: 'sin',
    cosname: 'cos',
    powname: 'pow',
}

def all_replacements():
    replacements = {}
    for name in namemap:
        for ty in ltypes.all_types:
            replacements[name + str(ty)] = namemap[name]

    return replacements

# ______________________________________________________________________

Ctx = namedtuple('Ctx', "engine module pm link")

def new_ctx():
    engine, mod, pm = test_support.make_llvm_context()

    replacements = all_replacements()
    # print(replacements)

    linker = linking.LLVMLinker()
    link = partial(linking.link_llvm_math_intrinsics,
                   engine, mod, libs.math_library, linker, replacements)
    return Ctx(engine, mod, pm, link)

def make_mod(ctx):
    m = types.ModuleType('testmod')
    llvm_support.wrap_llvm_module(ctx.module, ctx.engine, m)
    return m

# ______________________________________________________________________

def make_func(ctx, defname, callname, ty, nargs=1):
    fty = Type.function(ty, [ty]*nargs)
    f = ctx.module.add_function(fty, defname)
    bb = f.append_basic_block('entry')
    b = Builder.new(bb)

    lfunc = ctx.module.get_or_insert_function(fty, callname)
    ret = b.call(lfunc, f.args)
    b.ret(ret)

    return f

# ______________________________________________________________________

def call_complex_math(f, input):
    c_argty = f.argtypes[0]
    c_result = c_argty(0, 0)
    c_input = c_argty(input.real, input.imag)
    # c_input, c_result = ctypes.pointer(c_input), ctypes.pointer(c_result)
    c_result = f(c_input)
    return complex(c_result.e0, c_result.e1)

# ______________________________________________________________________
#                               TESTS

def test_link_real():
    ctx = new_ctx()
    def mkfunc(defname, callname, ty):
        return make_func(ctx, defname, callname + str(ty), ty)

    mkfunc('mysinf', sinname, ltypes.l_float)
    mkfunc('mysin',  sinname, ltypes.l_double)
    mkfunc('mysinl', sinname, ltypes.l_longdouble)

    # print(ctx.module)
    ctx.link()

    m = make_mod(ctx)
    our_result = m.mysinf(10.0), m.mysin(10.0), m.mysinl(10.0)
    exp_result = [math.sin(10.0)] * 3
    assert np.allclose(our_result, exp_result)

def test_link_complex():
    ctx = new_ctx()
    def mkfunc(defname, callname, ty):
        return make_func(ctx, defname, callname + str(ty), ty)

    # NOTE: we can't reliably call our function. TODO: pass by reference
    # mkfunc('mycsinf', sinname, ltypes.l_complex64)
    mkfunc('mycsin',  sinname, ltypes.l_complex128)
    # mkfunc('mycsinl', sinname, ltypes.l_complex256)

    # print(ctx.module)
    ctx.link()

    m = make_mod(ctx)
    input = 10+2j

    result = cmath.sin(input)

    our_result = (result, #test_support.call_complex_byval(m.mycsinf, input),
                  test_support.call_complex_byval(m.mycsin,  input),
                  result, #test_support.call_complex_byval(m.mycsinl, input)
                  )

    exp_result = [result] * 3
    assert np.allclose(our_result, exp_result), (our_result, exp_result)

def test_link_binary():
    ctx = new_ctx()
    ty = ltypes.l_complex128
    make_func(ctx, 'mypow', powname + str(ty), ty, nargs=2)
    ctx.link()
    m = make_mod(ctx)

    inputs = 2+2j, 3+3j
    result = test_support.call_complex_byval(m.mypow, *inputs)
    expect = pow(*inputs)

    print(result, expect)
    assert result == expect, (result, expect)