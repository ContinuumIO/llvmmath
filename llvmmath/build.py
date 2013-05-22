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
from subprocess import check_call

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

# ______________________________________________________________________
# Build targets

def build_bitcode(config):
    "Compile math library to bitcode with clang"
    check_call([config.clang, '-O3', '-march=native',
                '-c', 'mathcode.c', '-S', '-emit-llvm'] + includes, cwd=mathcode)

def build_shared(config):
    "Compile math library to a shared library with clang"
    check_call([config.clang, '-O3', '-march=native',
                '-c', 'mathcode.c', '-fPIC'] + includes, cwd=mathcode)
    check_call([config.clang, '-shared', 'mathcode.o',
                '-o', 'mathcode' + shared_ending], cwd=mathcode)

# ______________________________________________________________________
# Config

Config = namedtuple('Config', ['clang', 'conv_templ', 'targets', 'log'])

_default_values = {
    'clang':      'clang',
    'conv_templ': join(root, 'generator', 'conv_template.py'),
    'targets':    [build_bitcode], #, build_shared],
    'log':        logger.info,
}

default_config = Config(**_default_values)

def mkconfig(config, **override):
    return Config(**dict(zip(config._fields, config), **override))

# ______________________________________________________________________

def build(config=default_config):
    "Build the math library with Clang to bitcode and/or a shared library"
    config.log("Processing source files")

    args = [sys.executable, config.conv_templ]
    process = lambda fn: check_call(args + [fn])
    mkfn = partial(join, mathcode)

    process(mkfn('funcs.inc.src'))
    process(mkfn('npy_math_integer.c.src'))
    process(mkfn('npy_math_floating.c.src'))
    process(mkfn('npy_math_complex.c.src'))

    for build_target in config.targets:
        config.log("Building with target: %s" % build_target)
        build_target(config)

bitcode_fn = join(root, 'mathcode', 'mathcode.s')

def have_bitcode():
    "See whether we have compiled bitcode available"
    return exists(bitcode_fn)

def load_llvm_asm():
    "Load the math library as an LLVM module"
    if not exists(bitcode_fn):
        build(mkconfig(default_config, targets=[build_bitcode]))
    return llvm.core.Module.from_assembly(open(bitcode_fn))

#===------------------------------------------------------------------===
# Generate numpy config.h -- numpy/core/setup.py:generate_config_h
#===------------------------------------------------------------------===

from distutils.dep_util import newer

def generate_config_h(ext, build_dir):
        target = join(build_dir,header_dir,'config.h')
        d = os.path.dirname(target)
        if not os.path.exists(d):
            os.makedirs(d)

        if newer(__file__,target):
            config_cmd = config.get_config_cmd()
            log.info('Generating %s',target)

            # Check sizeof
            moredefs, ignored = cocache.check_types(config_cmd, ext, build_dir)

            # Check math library and C99 math funcs availability
            mathlibs = check_mathlib(config_cmd)
            moredefs.append(('MATHLIB',','.join(mathlibs)))

            check_math_capabilities(config_cmd, moredefs, mathlibs)
            moredefs.extend(cocache.check_ieee_macros(config_cmd)[0])
            moredefs.extend(cocache.check_complex(config_cmd, mathlibs)[0])

            # Signal check
            if is_npy_no_signal():
                moredefs.append('__NPY_PRIVATE_NO_SIGNAL')

            # Windows checks
            if sys.platform=='win32' or os.name=='nt':
                win32_checks(moredefs)

            # Inline check
            inline = config_cmd.check_inline()

            # Check whether we need our own wide character support
            if not config_cmd.check_decl('Py_UNICODE_WIDE', headers=['Python.h']):
                PYTHON_HAS_UNICODE_WIDE = True
            else:
                PYTHON_HAS_UNICODE_WIDE = False

            if ENABLE_SEPARATE_COMPILATION:
                moredefs.append(('ENABLE_SEPARATE_COMPILATION', 1))

            # Get long double representation
            if sys.platform != 'darwin':
                rep = check_long_double_representation(config_cmd)
                if rep in ['INTEL_EXTENDED_12_BYTES_LE',
                           'INTEL_EXTENDED_16_BYTES_LE',
                           'IEEE_QUAD_LE', 'IEEE_QUAD_BE',
                           'IEEE_DOUBLE_LE', 'IEEE_DOUBLE_BE',
                           'DOUBLE_DOUBLE_BE']:
                    moredefs.append(('HAVE_LDOUBLE_%s' % rep, 1))
                else:
                    raise ValueError("Unrecognized long double format: %s" % rep)

            # Py3K check
            if sys.version_info[0] == 3:
                moredefs.append(('NPY_PY3K', 1))

            # Generate the config.h file from moredefs
            target_f = open(target, 'w')
            for d in moredefs:
                if isinstance(d,str):
                    target_f.write('#define %s\n' % (d))
                else:
                    target_f.write('#define %s %s\n' % (d[0],d[1]))

            # define inline to our keyword, or nothing
            target_f.write('#ifndef __cplusplus\n')
            if inline == 'inline':
                target_f.write('/* #undef inline */\n')
            else:
                target_f.write('#define inline %s\n' % inline)
            target_f.write('#endif\n')

            # add the guard to make sure config.h is never included directly,
            # but always through npy_config.h
            target_f.write("""
#ifndef _NPY_NPY_CONFIG_H_
#error config.h should never be included directly, include npy_config.h instead
#endif
""")

            target_f.close()
            print('File:',target)
            target_f = open(target)
            print(target_f.read())
            target_f.close()
            print('EOF')
        else:
            mathlibs = []
            target_f = open(target)
            for line in target_f.readlines():
                s = '#define MATHLIB'
                if line.startswith(s):
                    value = line[len(s):].strip()
                    if value:
                        mathlibs.extend(value.split(','))
            target_f.close()

        # Ugly: this can be called within a library and not an extension,
        # in which case there is no libraries attributes (and none is
        # needed).
        if hasattr(ext, 'libraries'):
            ext.libraries.extend(mathlibs)

        incl_dir = os.path.dirname(target)
        if incl_dir not in config.numpy_include_dirs:
            config.numpy_include_dirs.append(incl_dir)

        return target

if __name__ == '__main__':
    build()