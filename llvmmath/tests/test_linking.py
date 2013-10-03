# -*- coding: utf-8 -*-
from __future__ import print_function, division, absolute_import

import ctypes
from collections import namedtuple
import math
import cmath

from llvmmath import ltypes, linking, libs, have_llvm_asm
from llvmmath.tests import support
from llvmmath.tests.support import parametrize

import numpy as np
from llvm.core import *

# ______________________________________________________________________

sinname = 'my_custom_sin'
cosname = 'my.custom.cos'
powname = 'my.special.pow'

namemap = {
    sinname: 'sin',
    cosname: 'cos',
    powname: 'pow',
}

mkname = lambda name, ty: '%s%d' % (name, ltypes.all_types.index(ty))

def all_replacements():
    replacements = {}
    for name in namemap:
        for ty in ltypes.all_types:
            replacements[mkname(name, ty)] = namemap[name]

    return replacements

# ______________________________________________________________________

class _Ctx(namedtuple('Ctx', "engine module pm lib linker, replacements")):
    def mkbyval(self, defname, callname, ty):
        return make_func(self, defname, mkname(callname, ty), ty)

    def mkbyref(self, defname, callname, ty):
        return make_func(self, defname, mkname(callname, ty), ty, byref=True)

    def link(self):
        engine, mod, pm, lib, linker, replacements = self
        linking.link_llvm_math_intrinsics(
            engine, mod, lib, linker, replacements)
        mod.verify()

        # Using the module optimizer to inline all functions remove a segfault
        # condition on 32-bit linux; thus, this is supporting the my guess
        # that bad ABI use is causing a stack corruption.
        # Eliminating the internal function call has successfully remove
        # the segfault.
        # TODO: replace all complex wrapping code
        pm.run(mod)

def new_ctx(lib, linker):
    engine, mod, pm = support.make_llvm_context()
    return _Ctx(engine, mod, pm, lib, linker, all_replacements())

def make_contexts():
    "Create LLVM contexts (_Ctx) for the .so and .s lib"
    so = libs.get_mathlib_so()
    so_linker = linking.ExternalLibraryLinker()
    ctx1 = new_ctx(lib=so, linker=so_linker)
    contexts = [ctx1]

    if have_llvm_asm():
        asm = libs.get_llvm_mathlib()
        asm_linker = linking.LLVMLinker()
        ctx2 = new_ctx(lib=asm, linker=asm_linker)
        contexts.append(ctx2)

    return contexts

def make_func(ctx, defname, callname, ty, nargs=1, byref=False):
    """
    Create an llvm function that calls an abstract math function. We
    use this to test linking, e.g. my_custom_sin(x) -> npy_sin(x)
    """
    fty = Type.function(ty, [ty] * nargs)
    wrapped = ctx.module.get_or_insert_function(fty, callname)
    if byref:
        wrap = support.create_byref_wrapper
    else:
        wrap = support.create_byval_wrapper

    return wrap(wrapped, defname)

#===------------------------------------------------------------------===
# Tests
#===------------------------------------------------------------------===

@parametrize(ctx=make_contexts())
def test_link_real(ctx):
    ctx.mkbyval('mysinf', sinname, ltypes.l_float)
    ctx.mkbyval('mysin',  sinname, ltypes.l_double)
    ctx.mkbyval('mysinl', sinname, ltypes.l_longdouble)

    # print(ctx.module)
    ctx.link()

    m = support.make_mod(ctx)
    our_result = m.mysinf(10.0), m.mysin(10.0), m.mysinl(10.0)
    exp_result = [math.sin(10.0)] * 3
    assert np.allclose(our_result, exp_result)

def _base_type(ty):
    return ty._type_._fields_[0][1] # Get the base type of a complex *

@parametrize(ctx=make_contexts())
def test_link_complex(ctx):
    ctx.mkbyref('mycsinf', sinname, ltypes.l_complex64)
    ctx.mkbyref('mycsin',  sinname, ltypes.l_complex128)
    ctx.mkbyref('mycsinl', sinname, ltypes.l_complex256)
    # print(ctx.module)
    ctx.link()
    print(ctx.module)

    m = support.make_mod(ctx)
    input = 10+2j

    result = cmath.sin(input)
    call = support.call_complex_byref

    typeof = lambda f: _base_type(f.argtypes[0])
    assert typeof(m.mycsinf) == ctypes.c_float
    assert typeof(m.mycsin) == ctypes.c_double, typeof(m.mycsin)
    assert typeof(m.mycsinl) in (ctypes.c_double, ctypes.c_longdouble)

    r1 = call(m.mycsinf, input)
    r2 = call(m.mycsin,  input)
    r3 = call(m.mycsinl, input)

    print("expect:", result)
    print("got:", r1, r2, r3)
    assert np.allclose([result] * 3, [r1, r2, r3])

# ______________________________________________________________________

@parametrize(ctx=make_contexts())
def test_link_binary(ctx):
    ty = ltypes.l_complex128
    make_func(ctx, 'mypow', mkname(powname, ty), ty, nargs=2, byref=True)
    ctx.link()
    m = support.make_mod(ctx)
    print(ctx.module)

    assert list(map(_base_type, m.mypow.argtypes)) == [ctypes.c_double] * 3
    assert m.mypow.restype is None

    inputs = 2+2j, 3+3j
    result = support.call_complex_byref(m.mypow, *inputs)
    expect = pow(*inputs)

    print(result, expect)
    assert np.allclose([result], [expect]), (result, expect)

# ______________________________________________________________________

@parametrize(ctx=make_contexts())
def test_link_external(ctx):
    pass

# ctx, = make_contexts()[1]
# test_link_complex(ctx)
