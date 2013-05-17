# -*- coding: utf-8 -*-
from __future__ import print_function, division, absolute_import

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
