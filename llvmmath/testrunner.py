# -*- coding: utf-8 -*-

"""
Run llvmmath tests.
"""

from __future__ import print_function, division, absolute_import

import os, sys
import numpy
from os.path import join, dirname, abspath

from llvmmath import __version__

def test(verbosity=1, xunitfile=None, exit=False):
    """
    Runs the full llvmmath test suite.

    Parameters
    ----------
    verbosity : int, optional
        Value 0 prints very little, 1 prints a little bit,
        and 2 prints the test names while testing.
    xunitfile : string, optional
        If provided, writes the test results to an xunit
        style xml file. This is useful for running the tests
        in a CI server such as Jenkins.
    exit : bool, optional
        If True, the function will call sys.exit with an
        error code after the tests are finished.
    """
    import pytest

    print('Running llvmmath unit tests')
    print('===========================')
    print('Python version: %s' % sys.version)
    print('Python prefix: %s' % sys.prefix)
    print('---------------------------')
    print('llvmmath module: %s' % os.path.dirname(__file__))
    print('llvmmath version: %s' % __version__)
    print('NumPy version: %s' % numpy.__version__)
    print('---------------------------')

    sys.stdout.flush()
    cwd = os.getcwd()
    try:
        os.chdir(dirname(dirname(abspath(__file__))))
        ret = pytest.main([#'--verbosity=%d' % verbosity,
                           #'--with-xunit',
                           #'--xunit-file=%s' % xunitfile,
                           join(dirname(abspath(__file__)), 'tests')])
    finally:
        os.chdir(cwd)

    if exit:
        raise SystemExit(ret)
    return ret

test.__test__ = False