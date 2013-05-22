Supported functions
===================

Support symbols and signatures are listed below. The types expand as follows:

    * ``int`` : int, long, long long
    * ``float``: float, double, long double
    * ``complex``: float complex, double complex, long double complex

So a signature ``float sin(float)`` signals the availability of:

    * ``float sinf(float)``
    * ``double sin(double)``
    * ``long double sinl(long double)``

The list of symbols is below:

.. literalinclude:: ../llvmmath/RequiredSymbols.txt
    :language: c
    :linenos:
