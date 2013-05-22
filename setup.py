# -*- coding: utf-8 -*-
from __future__ import print_function, division, absolute_import

import os
import sys
from itertools import imap, ifilter
from fnmatch import fnmatchcase
from os.path import join, dirname, abspath, isfile
from distutils.util import convert_path
from distutils.core import setup, Extension

import llvmmath.build

import numpy

# python 3
map = lambda *args: list(imap(*args))
filter = lambda *args: list(ifilter(*args))

#===------------------------------------------------------------------===
# Setup constants and arguments
#===------------------------------------------------------------------===

setup_args = {
    'long_description': open('README.md').read(),
}

root = dirname(abspath(__file__))
mathcode_root = join(root, 'llvmmath', 'mathcode')
mathcode_private = join(mathcode_root, 'private')
mathcode_depends = (filter(isfile, os.listdir(mathcode_root)) +
                    os.listdir(mathcode_private))

exclude_packages = ()
cmdclass = {}

#===------------------------------------------------------------------===
# Package finding
#===------------------------------------------------------------------===

def find_packages(where='.', exclude=()):
    out = []
    stack=[(convert_path(where), '')]
    while stack:
        where, prefix = stack.pop(0)
        for name in os.listdir(where):
            fn = os.path.join(where,name)
            if ('.' not in name and os.path.isdir(fn) and
                os.path.isfile(os.path.join(fn, '__init__.py'))
            ):
                out.append(prefix+name)
                stack.append((fn, prefix+name+'.'))

    if sys.version_info[0] == 3:
        exclude = exclude + ('*py2only*', )

    for pat in list(exclude) + ['ez_setup', 'distribute_setup']:
        out = [item for item in out if not fnmatchcase(item, pat)]

    return out

#===------------------------------------------------------------------===
# 2to3
#===------------------------------------------------------------------===

def run_2to3():
    import lib2to3.refactor
    from distutils.command.build_py import build_py_2to3 as build_py
    print("Installing 2to3 fixers")
    # need to convert sources to Py3 on installation
    fixes = 'dict imports imports2 unicode ' \
            'xrange itertools itertools_imports long types'.split()
    fixes = ['lib2to3.fixes.fix_' + fix
             for fix in fixes]
    build_py.fixer_names = fixes
    cmdclass["build_py"] = build_py

#===------------------------------------------------------------------===
# Generate code for build
#===------------------------------------------------------------------===

llvmmath.build.build()

#===------------------------------------------------------------------===
# setup
#===------------------------------------------------------------------===

setup(
    name="llvmmath",
    version=llvmmath.__version__,
    author="Continuum Analytics, Inc.",
    license="BSD",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.2",
        "Topic :: Utilities",
    ],
    description="LLVM math library",
    packages=find_packages(exclude=exclude_packages),
    package_data={
        '': ['*.md', '*.cfg'],
        'llvmmath.mathcode': ['*.c', '*.h', '*.src', 'README', 'private/*.h'],
    },
    ext_modules=[
        Extension(
            name="llvmmath.mathcode.mathcode",
            sources=["llvmmath/mathcode/mathcode.c"],
            include_dirs=[numpy.get_include(), mathcode_root, mathcode_private],
            depends=mathcode_depends),
    ],
    cmdclass=cmdclass,
    **setup_args
)