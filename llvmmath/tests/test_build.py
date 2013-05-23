# -*- coding: utf-8 -*-
from __future__ import print_function, division, absolute_import

import os
from os.path import join, dirname, abspath, exists
import ctypes
import types
import math

from .. import llvm_support, build, have_llvm_asm, have_clang
from . import support

pkgdir = dirname(dirname(abspath(__file__)))
mathcode = join(pkgdir, 'mathcode')
mathcode_so  = join(mathcode, 'mathcode' + build.find_shared_ending())
mathcode_asm = join(mathcode, 'mathcode.s')

# ______________________________________________________________________

@support.skip_if(not have_clang())
def test_build_shared():
    "Test building and getting and using the shared library"
    if exists(mathcode_so):
        os.remove(mathcode_so)

    config = build.mkconfig(build.default_config, targets=[build.build_shared])
    build.build(config=config)
    assert exists(mathcode_so)

    mod = ctypes.CDLL(mathcode_so)
    mod.npy_sin.restype = ctypes.c_double
    mod.npy_sin.argtypes = [ctypes.c_double]

    result = mod.npy_sin(ctypes.c_double(10.0))
    expect = math.sin(10.0)
    assert result == expect, (result, expect)

# ______________________________________________________________________

@support.skip_if(not have_clang())
def test_build_llvm():
    "Test building llvm and getting and using the resulting llvm module"
    if exists(mathcode_asm):
        os.remove(mathcode_asm)

    config = build.mkconfig(build.default_config, targets=[build.build_llvm])
    build.build(config=config)
    assert exists(mathcode_asm)

    test_get_llvm_lib()

# ______________________________________________________________________

@support.skip_if(not have_llvm_asm())
def test_get_llvm_lib():
    "Test getting the llvm lib from a clean environment"
    if exists(mathcode_asm):
        os.remove(mathcode_asm)

    lctx = support.make_llvm_context()
    lmod = build.load_llvm_asm()
    mod = types.ModuleType('llvmmod')
    llvm_support.wrap_llvm_module(lmod, lctx.engine, mod)

    result = mod.npy_sin(ctypes.c_double(10.0))
    expect = math.sin(10.0)
    assert result == expect, (result, expect)

# ______________________________________________________________________