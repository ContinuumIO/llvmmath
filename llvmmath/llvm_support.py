# -*- coding: utf-8 -*-

"""
Bind LLVM functions to ctypes.
Originally adapated from Bitey, blaze/blir/bind.py.
"""

from __future__ import print_function, division, absolute_import

from functools import partial
import logging
import ctypes
import io
import os
import sys

from llvm.core import Module
import llvm.core
import llvm.ee

logger = logging.getLogger(__name__)

PY3 = sys.version_info[0] >= 3

def map_llvm_to_ctypes(llvm_type, py_module=None):
    '''
    Map an LLVM type to an equivalent ctypes type. py_module is an
    optional module that is used for structure wrapping.  If
    structures are found, the struct definitions will be created in
    that module.
    '''
    kind = llvm_type.kind
    if kind == llvm.core.TYPE_INTEGER:
        if llvm_type.width < 8:
            return ctypes.c_int8
        ctype = getattr(ctypes,"c_int"+str(llvm_type.width))

    elif kind in (llvm.core.TYPE_X86_FP80,
                  llvm.core.TYPE_PPC_FP128,
                  llvm.core.TYPE_FP128):
        ctype = ctypes.c_longdouble

    elif kind == llvm.core.TYPE_DOUBLE:
        ctype = ctypes.c_double

    elif kind == llvm.core.TYPE_FLOAT:
        ctype = ctypes.c_float

    elif kind == llvm.core.TYPE_VOID:
        ctype = None

    elif kind == llvm.core.TYPE_POINTER:
        pointee = llvm_type.pointee
        p_kind = pointee.kind
        if p_kind == llvm.core.TYPE_INTEGER:
            width = pointee.width

            # Special case:  char * is mapped to strings
            if width == 8:
                ctype = ctypes.c_char_p
            else:
                ctype = ctypes.POINTER(map_llvm_to_ctypes(pointee, py_module))

        # Special case: void * mapped to c_void_p type
        elif p_kind == llvm.core.TYPE_VOID:
            ctype = ctypes.c_void_p
        else:
            ctype = ctypes.POINTER(map_llvm_to_ctypes(pointee, py_module))

    elif kind == llvm.core.TYPE_STRUCT:
        # Be careful accessing name:
        #     python: Type.cpp:580: llvm::StringRef llvm::StructType::getName()
        #                           const: Assertion `!isLiteral() &&
        #                           "Literal structs never have names"' failed.
        struct_name = str(llvm_type)

        # If the named type is already known, return it
        if hasattr(py_module, struct_name):
            return getattr(py_module, struct_name, None)

        names = [ "e" + str(n) for n in range(llvm_type.element_count) ]

        if py_module:
            # avoid recursion on self-referential fields
            setattr(py_module, struct_name, None)

        fields = [(name, map_llvm_to_ctypes(elem, py_module))
                      for name, elem in zip(names, llvm_type.elements)]
        if any(f[1] is None for f in fields):
            return None

        class ctype(ctypes.Structure):
            # We can't set fields afterwards: "TypeError: fields are final" in py3
            _fields_ = fields

        if py_module:
            setattr(py_module, struct_name, ctype)

    elif kind == llvm.core.TYPE_ARRAY:
        return map_llvm_to_ctypes(llvm_type.element, py_module) * llvm_type.count

    elif kind == llvm.core.TYPE_VECTOR:
        return map_llvm_to_ctypes(llvm_type.element, py_module) * llvm_type.count

    elif kind == llvm.core.TYPE_FUNCTION:
        ctype = ctypes.CFUNCTYPE(
            map_llvm_to_ctypes(llvm_type.return_type),
            *[map_llvm_to_ctypes(a) for a in llvm_type.args])

    else:
        if py_module:
            logger.warn("Unknown type: %s" % llvm_type)
            return None
        raise TypeError("Unknown type: %s" % llvm_type)

    return ctype

def get_ctypes_wrapper(func, engine, map_llvm_to_ctypes=map_llvm_to_ctypes):
    args = func.type.pointee.args
    ret_type = func.type.pointee.return_type

    ret_ctype = map_llvm_to_ctypes(ret_type)
    args_ctypes = [map_llvm_to_ctypes(arg) for arg in args]

    # Declare the ctypes function prototype
    functype = ctypes.CFUNCTYPE(ret_ctype, *args_ctypes)

    # Get the function point from the execution engine
    addr = engine.get_pointer_to_function(func)

    # Make a ctypes callable out of it
    return functype(addr)

def wrap_llvm_function(func, engine, py_module):
    '''
    Create a ctypes wrapper around an LLVM function.
    engine is the LLVM execution engine.
    func is an LLVM function instance.
    py_module is a Python module where to put the wrappers.
    '''
    ctypes_mapper = partial(map_llvm_to_ctypes, py_module=py_module)
    wrapper = get_ctypes_wrapper(func, engine, ctypes_mapper)
    # Set it in the module
    setattr(py_module, func.name, wrapper)
    wrapper.__name__ = func.name

def wrap_llvm_module(llvm_module, engine, py_module):
    '''
    Build ctypes wrappers around an existing LLVM module and execution
    engine.  py_module is an existing Python module that will be
    populated with the resulting wrappers.
    '''
    functions = [func for func in llvm_module.functions
                 if not func.name.startswith("_")
                 and not func.name.startswith("Py")
                 and not func.is_declaration
                 and func.linkage == llvm.core.LINKAGE_EXTERNAL]
    for func in functions:
        wrap_llvm_function(func, engine, py_module)

def wrap_llvm_bitcode(bitcode, py_module):
    '''
    Given a byte-string of LLVM bitcode and a Python module,
    populate the module with ctypes bindings for public methods
    in the bitcode.
    '''
    llvm_module = Module.from_bitcode(io.BytesIO(bitcode))
    engine = llvm.ee.ExecutionEngine.new(llvm_module)
    wrap_llvm_module(llvm_module, engine, py_module)
    setattr(py_module, '_llvm_module', llvm_module)
    setattr(py_module, '_llvm_engine', engine)
