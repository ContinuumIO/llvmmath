# -*- coding: utf-8 -*-

"""
Some test helpers.
"""

from __future__ import print_function, division, absolute_import

import sys
import types
import ctypes
import unittest
import functools
import itertools
import collections

from .. import llvm_support
from .. complex_support import have_lfunc, create_byref_wrapper, print_complex

import llvm.core as lc
import llvm.passes as lp
import llvm.ee as le

LLVMContext = collections.namedtuple("LLVMContext", "engine module pm")

def make_llvm_context(name="mymodule"):
    "Return an LLVM context (engine, module, passmanager)"
    module = lc.Module.new("executable_module")
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

def build_complex_args(argtypes, *inputs):
    c_args = []
    for c_argty, input in zip(argtypes, inputs):
        c_args.append(c_argty(input.real, input.imag))
    return c_args

def call_complex_byval(f, *inputs):
    "Call complex function by value, e.g. complex func(complex)"
    c_args = build_complex_args(f.argtypes, *inputs)
    c_result = f(*c_args)
    return complex(c_result.e0, c_result.e1)

def call_complex_byref(f, *inputs):
    """
    Call complex function by reference, e.g. void sin(complex *in, complex *out)
    """
    c_resty = f.argtypes[1]._type_ # get base type from pointer argtype
    c_result = c_resty(0)

    c_args = build_complex_args([pty._type_ for pty in f.argtypes], *inputs)
    c_args.append(c_result)
    c_args = list(map(ctypes.pointer, c_args))

    # What? ArgumentError: argument 3: <type 'exceptions.TypeError'>: expected
    # LP_ instance instead of LP_
    f.argtypes = [type(a) for a in c_args]
    # -- end hack
    f(*c_args)

    if issubclass(c_resty, ctypes.Structure):
        return complex(c_result.e0, c_result.e1)
    return c_result

#===------------------------------------------------------------------===
# Function wrapping
#===------------------------------------------------------------------===

def create_byval_wrapper(wrapped, name):
    """
    Create a simple function wrapper for testing.
    """
    mod = wrapped.module
    assert not have_lfunc(mod, name)

    f = mod.add_function(wrapped.type.pointee, name)
    bb = f.append_basic_block('entry')
    b = lc.Builder.new(bb)
    ret = b.call(wrapped, f.args)
    b.ret(ret)
    return f

#===------------------------------------------------------------------===
# Testing
#===------------------------------------------------------------------===

def skip_if(cond, msg="Skipping"):
    def dec(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            if cond and sys.version_info[:2] < (2, 7):
                print("Skipping test:", msg)
            elif cond:
                raise unittest.SkipTest(msg)
            else:
                return f(*args, **kwargs)
        return wrapper
    return dec


def test(f):
    class Test(unittest.TestCase):
        pass

    @functools.wraps(f)
    def test_something(self):
        f()

    setattr(Test, f.__name__, test_something)
    Test.__name__ = f.__name__.title().replace("_", "")
    return Test

def parametrize(**named_parameters):
    """
        @parametrize(x=['foo', 'bar'], y=['baz', 'quux'])
        def test_func(x, y):
            print x, y # prints all combinations

    Generates a unittest TestCase in the function's global scope named
    'test_func_testcase' with parametrized test methods.

    ':return: The original function
    """
    def decorator(func):
        class TestCase(unittest.TestCase):
            pass

        TestCase.__name__ = func.__name__
        names = named_parameters.keys()
        values = itertools.product(*named_parameters.values())

        for i, parameter in enumerate(values):
            name = 'test_%s_%d' % (func.__name__, i)

            if names:
                def testfunc(self, parameter=parameter):
                    return func(**dict(zip(names, parameter)))
            else:
                def testfunc(self, parameter=parameter):
                    return func(parameter)

            testfunc.__name__ = name
            if func.__doc__:
                testfunc.__doc__ = func.__doc__.replace(func.__name__, name)

            setattr(TestCase, name, testfunc)


        func.__globals__[func.__name__ + '_testcase'] = TestCase
        return func

    return decorator