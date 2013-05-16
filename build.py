# -*- coding: utf-8 -*-

"""
Build math C modules and compile to LLVM bitcode.
"""

from __future__ import print_function, division, absolute_import

import os
import sys
from distutils import sysconfig
from os.path import join, dirname
from subprocess import check_call

from numba.pycc import compiler

import numpy as np

root = dirname(__file__)
mathcode = join(root, 'mathcode')
shared_ending = compiler.find_shared_ending()

default_config = {
    'CLANG':      'clang',
    'CONV_TEMPL': join('generator', 'conv_template.py'),
    'OUTPUT':     'shared', #'bitcode',
}

incdirs = [np.get_include(), sysconfig.get_python_inc(), join(mathcode, 'private')]
includes = ['-I' + dir for dir in incdirs]

def build(config=default_config):
    # Process .*.src files
    check_call([sys.executable, config['CONV_TEMPL'],
                join(mathcode, 'funcs.inc.src')])
    check_call([sys.executable, config['CONV_TEMPL'],
                join(mathcode, 'npy_math_floating.c.src')])
    check_call([sys.executable, config['CONV_TEMPL'],
                join(mathcode, 'npy_math_complex.c.src')])

    bitcode = config['OUTPUT'] == 'bitcode'
    if bitcode:
        args = ['-S']
    else:
        args = ['-fPIC']

    # Compile to bitcode with clang
    check_call([config['CLANG'], '-emit-llvm', '-O4', '-march=native',
                '-c', 'mathcode.c'] + args + includes, cwd=mathcode)

    if not bitcode:
        check_call([config['CLANG'], '-shared', 'mathcode.o',
                    '-o', 'mathcode' + shared_ending], cwd=mathcode)

#------------------------------------------------------------------------
# Generate numpy config.h -- numpy/core/setup.py:generate_config_h
#------------------------------------------------------------------------

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