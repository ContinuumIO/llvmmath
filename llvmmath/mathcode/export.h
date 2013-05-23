#include <Python.h>

#ifndef __LLVMMATH_EXTERN_C
  #ifdef __cplusplus
    #define __LLVMMATH_EXTERN_C extern "C"
  #else
    #define __LLVMMATH_EXTERN_C extern
  #endif
#endif

#ifndef DL_IMPORT
  #define DL_IMPORT(t) t
#endif
#ifndef DL_EXPORT
  #define DL_EXPORT(t) t
#endif

#define __LLVMMATH_IMPORT(t) DL_IMPORT(t)
#define __LLVMMATH_EXPORT(t) DL_EXPORT(t)