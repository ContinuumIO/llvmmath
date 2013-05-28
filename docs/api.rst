Public API
==========

llvmmath exposes an interface to load math libraries and optionally link
them into an existing LLVM module.

Loading Libraries
-----------------

Libraries can be loaded and queried for available and missing symbols.
The default math library is the one shipped with llvmmath:

.. code-block:: pycon

    >>> import llvmmath
    >>> lib = llvmmath.get_default_math_lib()
    >>> lib.missing
    []
    >>> lib.symbols
    Library(
        double abs(double): npy_fabs
        float abs({ float, float }): nc_cabsf
        ...)

Note the signature for the second ``abs()``, which takes a ``{ float, float }``
argument. This is a ``float complex`` type.

Types
-----

The types in llvmmath are available in the ltypes module, and are named
as follows:

    * l_int, l_long, l_longlong
    * l_float, l_double, l_longdouble
    * l_complex64, l_complex128, l_complex256

.. code-block:: pycon

    >>> from llvmmath import types
    >>> print ltypes.l_complex128
    { double, double }

    >>> from llvmmath import ltypes
    >>> print ltypes.l_complex128
    { double, double }

Linking Libraries
-----------------
A useful feature is to link a math library into an existing LLVM module that
wants to use math. This can be achieved with the ``llvmmath.linking`` module:

.. function:: link_llvm_math_intrinsics(engine, module, library, linker, replacements)

    :param engine: llvm execution engine
    :param module: llvm module containing math calls
    :param library: ``llvmmath.math_support.Library`` of math symbols
    :param linker: linker that can link the math library
    :type linker: ``llvmmath.linking.Linker``
    :param replacements: { abstract_math_name -> math_name }
    :type replacements: dict of str -> str

Let's say we have a module like this:

.. code-block:: llvm

    declare { float, float } @myproject.math.sin({ float, float })

    define void @my_func({ float, float }*) {
    entry:
      %sin_arg = load { float, float }* %0
      %sin_result = call { float, float } @myproject.math.sin({ float, float } %2)
      ...
    }

And we want to resolve ``myproject.math.sin`` to link to the math library.
We can do this as follows:

.. code-block:: pycon

    >>> import llvmmath
    >>> from llvmmath import linking
    >>> lib = llvmmath.get_default_math_lib()
    >>> linker = linking.get_linker(lib)
    >>> replacements = { 'myproject.math.sin' : 'sin' }
    >>> linking.link_llvm_math_intrinsics(engine, module, lib, linker, replacements)

If we now inspect our module we should find something along the lines of:

.. code-block:: llvm

    define void @my_func({ float, float }*) {
    entry:
      %sin_arg = load { float, float }* %0
      %sin_result = call { float, float } @llvmmath.complexwrapper.my_custom_sin({ float, float } %2)
      ...
    }

    define { float, float } @llvmmath.complexwrapper.my_custom_sin({ float, float }) {
    entry:
      %result = alloca { float, float }
      %arg = alloca { float, float }
      store { float, float } %0, { float, float }* %arg
      %1 = bitcast { float, float }* %arg to %struct.npy_cfloat.0*
      %2 = bitcast { float, float }* %result to %struct.npy_cfloat.0*
      call void @nc_sinf(%struct.npy_cfloat.0* %1, %struct.npy_cfloat.0* %2)
      %3 = load { float, float }* %result
      ret { float, float } %3
    }

    define void @nc_sinf(%struct.npy_cfloat.0* nocapture %x, %struct.npy_cfloat.0* nocapture %r) nounwind uwtable {
      ...
    }

The linker will replace the function call to a wrapper which passes arguments
by reference to the actual implementation. We pass complex numbers by
reference to avoid ABI problems. Note that the IR above may look a little
different when the LLVM assembly of the math implementation is not available
(if clang is not installed or not working).

.. NOTE:: Functions with different signatures must have different function names (i.e.,
          they must be different function symbols).
          E.g. if you're calling ``sin(double)`` and ``sin(float)``, you need a replacement
          scheme that maps ``{ 'myproject.double.sin': 'sin', 'myproject.float.sin': 'sin' }``.

Use outside of Python
---------------------

TODO
