# -*- coding: utf-8 -*-
from __future__ import print_function, division, absolute_import

import os
from os.path import join, dirname, abspath, exists
import ctypes
import types
import math
import tempfile
import shutil

from llvmmath import llvm_support, build, have_llvm_asm, have_clang
from llvmmath.tests.support import test, skip_if, make_llvm_context

writable = lambda dirname: os.access(dirname, os.W_OK)

# ______________________________________________________________________

@test
@skip_if(not writable(dirname(dirname(abspath(__file__)))))
@skip_if(not have_clang())
def test_build_llvm():
    "Test building llvm and getting and using the resulting llvm module"
    tempdir = tempfile.mkdtemp()
    try:
        asmfile = join(tempdir, 'mathcode.s')
        config = build.mkconfig(build.default_config,
                                targets=[build.build_llvm],
                                output_dir=tempdir)
        build.build_targets(config=config)
        assert exists(asmfile)
        get_llvm_lib(asmfile)
    finally:
        shutil.rmtree(tempdir)

print(test_build_llvm, vars(test_build_llvm))
#
# ______________________________________________________________________

@skip_if(not have_llvm_asm())
def get_llvm_lib(asmfile=None):
    "Test getting the llvm lib from a clean environment"
    lctx = make_llvm_context()
    kwds = { 'asmfile': asmfile } if asmfile else {}
    lmod = build.load_llvm_asm(**kwds)
    mod = types.ModuleType('llvmmod')
    llvm_support.wrap_llvm_module(lmod, lctx.engine, mod)

    result = mod.npy_sin(ctypes.c_double(10.0))
    expect = math.sin(10.0)
    assert result == expect, (result, expect)

test_get_llvm_lib = test(get_llvm_lib)

# ______________________________________________________________________
