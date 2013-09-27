# -*- coding: utf-8 -*-

"""
Build math C modules and compile to LLVM assembly code.
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

from .utils import cached
from .generator import generate_config

import llvm.core
import numpy as np

logger = logging.getLogger(__name__)

# ______________________________________________________________________

def find_shared_ending():
    return sysconfig.get_config_var('SO')

root = dirname(__file__)
mathcode = join(root, 'mathcode')

incdirs = [np.get_include(), sysconfig.get_python_inc(), join(mathcode, 'private')]
includes = ['-I' + abspath(dir) for dir in incdirs]

#===------------------------------------------------------------------===
# Build Targets
#===------------------------------------------------------------------===

def build_llvm(config):
    "Compile math library to bitcode with clang"
    outfile = join(config.output_dir, 'mathcode.s')
    # use the most generic target triple
    ## arch
    if tuple.__itemsize__ == 8:
        target = 'x86_64'
    else:
        target = 'i386'
    ## OS
    if sys.platform.startswith('win32'):
        target += '-win32'
    elif sys.platform.startswith('darwin'):
        target += '-macosx'
    elif sys.platform.startswith('linux'):
        target += '-linux'
    else: # unknown platform, maybe it does not need the OS info
        pass
    # Disable optimization to leave more information to the client.
    # The client can then specialize to the specific hardware just-in-time.
    check_call([config.clang, '-O0', '-target', target, '-c', 'mathcode.c',
                '-S', '-emit-llvm', '-o', outfile] + includes,
               cwd=mathcode)

#===------------------------------------------------------------------===
# Config
#===------------------------------------------------------------------===

Config = namedtuple('Config', 'clang conv_templ targets log output_dir')

_default_values = {
    'clang':        'clang',
    'conv_templ':   join(root, 'generator', 'conv_template.py'),
    'targets':      [build_llvm], #, build_shared],
    'log':          logger.info,
    'output_dir':   mathcode,
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

asmfile = join(root, 'mathcode', 'mathcode.s')

def have_llvm_asm():
    "See whether we have compiled llvm assembly available"
    return exists(asmfile)

@cached
def have_clang():
    "See whether we have clang installed and working"
    try:
        return call(['clang', '--help'], stdout=PIPE) == 0
    except EnvironmentError:
        return False

def load_llvm_asm(asmfile=asmfile):
    "Load the math library as an LLVM module"
    if not exists(asmfile):
        build(mkconfig(default_config, targets=[build_llvm]))
    with open(asmfile) as fin:
        mod = llvm.core.Module.from_assembly(fin)
    return mod

if __name__ == '__main__':
    build()
