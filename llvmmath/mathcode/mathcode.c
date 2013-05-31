#include "export.h"

#include "funcs.inc"
#include "npy_math_integer.c"
#include "npy_math_floating.c"
#include "npy_math_complex.c"
#include "ieee754.c"

/* Make it an extension module to make windows happy */
#if PY_MAJOR_VERSION >= 3
  #define MOD_ERROR_VAL NULL
  #define MOD_SUCCESS_VAL(val) val
  #define MOD_INIT(name) PyMODINIT_FUNC PyInit_##name(void)
  #define MOD_DEF(ob, name, doc, methods) { \
          static struct PyModuleDef moduledef = { \
            PyModuleDef_HEAD_INIT, name, doc, -1, methods, }; \
          ob = PyModule_Create(&moduledef); }
#else
  #define MOD_ERROR_VAL
  #define MOD_SUCCESS_VAL(val)
  #define MOD_INIT(name) void init##name(void)
  #define MOD_DEF(ob, name, doc, methods) \
          ob = Py_InitModule3(name, methods, doc);
#endif

static PyMethodDef ext_methods[] = {
    { NULL }
};

MOD_INIT(mathcode)
{
    PyObject *m;

    MOD_DEF(m, "mathcode", "Math library", ext_methods)

    if (m == NULL)
        return MOD_ERROR_VAL;

    return MOD_SUCCESS_VAL(m);
}
