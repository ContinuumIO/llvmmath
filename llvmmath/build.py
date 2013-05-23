# -*- coding: utf-8 -*-

"""
Build math C modules and compile to LLVM bitcode.
"""

from __future__ import print_function, division, absolute_import

import os
import sys
import logging
from distutils import sysconfig
from functools import partial
from collections import namedtuple
from os.path import join, dirname, abspath, exists
from subprocess import call, check_call, PIPE

from .generator import generate_config

import llvm.core
import numpy as np

logger = logging.getLogger(__name__)

# ______________________________________________________________________

_shared_endings = { 'win': '.dll', 'dar': '.so', 'default': ".so", }

def find_shared_ending():
    return _shared_endings.get(sys.platform[:3], _shared_endings['default'])

root = dirname(__file__)
mathcode = join(root, 'mathcode')
shared_ending = find_shared_ending()

incdirs = [np.get_include(), sysconfig.get_python_inc(), join(mathcode, 'private')]
includes = ['-I' + abspath(dir) for dir in incdirs]

#===------------------------------------------------------------------===
# Build Targets
#===------------------------------------------------------------------===

def build_llvm(config):
    "Compile math library to bitcode with clang"
    check_call([config.clang, '-O3', '-march=native',
                '-c', 'mathcode.c', '-S', '-emit-llvm'] + includes, cwd=mathcode)

def build_shared(config):
    "Compile math library to a shared library with clang"
    check_call([config.clang, '-O3', '-march=native',
                '-c', 'mathcode.c', '-fPIC'] + includes, cwd=mathcode)
    check_call([config.clang, '-shared', 'mathcode.o',
                '-o', 'mathcode' + shared_ending], cwd=mathcode)

#===------------------------------------------------------------------===
# Config
#===------------------------------------------------------------------===

Config = namedtuple('Config', ['clang', 'conv_templ', 'targets', 'log'])

_default_values = {
    'clang':      'clang',
    'conv_templ': join(root, 'generator', 'conv_template.py'),
    'targets':    [build_llvm], #, build_shared],
    'log':        logger.info,
}

default_config = Config(**_default_values)

def mkconfig(config, **override):
    return Config(**dict(zip(config._fields, config), **override))

#===------------------------------------------------------------------===
# Building
#===------------------------------------------------------------------===

def build(config=default_config):
    "Build the math library with Clang to bitcode and/or a shared library"
    build_source(config)
    build_targets(config)

def build_source(config=default_config):
    config.log("Processing source files")

    args = [sys.executable, config.conv_templ]
    process = lambda fn: check_call(args + [fn])
    mkfn = partial(join, mathcode)

    process(mkfn('funcs.inc.src'))
    process(mkfn('npy_math_integer.c.src'))
    process(mkfn('npy_math_floating.c.src'))
    process(mkfn('npy_math_complex.c.src'))
    process(mkfn('ieee754.c.src'))

    # Generate config.h
    config.log("Writing config.h")
    f = open(join(mathcode, 'private', 'config.h'), 'w')
    generate_config.generate_config(f)

def build_targets(config=default_config):
    for build_target in config.targets:
        config.log("Building with target: %s" % build_target.__name__)
        build_target(config)

# ______________________________________________________________________

bitcode_fn = join(root, 'mathcode', 'mathcode.s')

def have_llvm_asm():
    "See whether we have compiled llvm assembly available"
    return exists(bitcode_fn)

def have_clang():
    "See whether we have clang installed and working"
    try:
        return call(['clang', '--help'], stdout=PIPE) == 0
    except EnvironmentError:
        return False

def load_llvm_asm():
    "Load the math library as an LLVM module"
    if not exists(bitcode_fn):
        build(mkconfig(default_config, targets=[build_llvm]))
    return llvm.core.Module.from_assembly(open(bitcode_fn))

if __name__ == '__main__':
    build()