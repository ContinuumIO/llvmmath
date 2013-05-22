.. llvmmath documentation master file, created by
   sphinx-quickstart on Wed May 22 22:48:13 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

llvmmath
====================================

The purpose of this project is to provide portable math functions, many of
which are in C99. It is based on NumPy's umath and tries to support all
floating point and complex types.

The library can be compiled with any C compiler, or to LLVM assembly using
Clang, to be linked into modules containing functions for jitting.

Installing
==========

.. code-block:: bash

    $ git clone git@github.com:ContinuumIO/llvmmath.git
    $ cd llvmmath
    $ python setup.py install

Documentation
=============

Contents:

.. toctree::
   :maxdepth: 2

   symbols.rst
   api.rst

.. Indices and tables
.. ==================

.. * :ref:`genindex`
.. * :ref:`modindex`
.. * :ref:`search`

