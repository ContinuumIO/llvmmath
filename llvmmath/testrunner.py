# -*- coding: utf-8 -*-

"""
Run llvmmath tests.

Adapted from dynd-python:

    dynd/__init__.py , May 20 2013
    git hash: ffefccbabda55bd0af25d0203a2715378acb5c8e
"""

from __future__ import print_function, division, absolute_import

import os, sys
import numpy
from os.path import join, dirname, abspath

from llvmmath import __version__

def test(verbosity=1, xunitfile=None, exit=False):
    """
    Runs the full numba test suite, outputing
    the results of the tests to  sys.stdout.

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

    # Use nose to run the tests and produce an XML file
    import nose
    return nose.main(argv=['nosetests',
                    '--verbosity=%d' % verbosity,
                    '--with-xunit',
                    '--xunit-file=%s' % xunitfile,
                    join(dirname(abspath(__file__)), 'tests')],
                 exit=exit)

test.__test__ = False
