/* 
   Copyright (c) 2002 Zope Corporation and Contributors.
   All Rights Reserved.
 
   This software is subject to the provisions of the Zope Public License,
   Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
   THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
   WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
   WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
   FOR A PARTICULAR PURPOSE.
*/
 
#include <time.h>

/* Conceptually an enum is appropriate, but we may want to pack the
   enum into a very small number of bits -- say 2 or 3.  When we get
   to this level of optimization, we'll probably need a collection of
   #define constants.
*/

enum PyPersist_State { UPTODATE, CHANGED, STICKY, GHOST };

/* The PyPersist_HEAD defines the minimal slots needed by a persistent
   object.  It exists to support types like BTrees that are defined in
   C extension modules.

   PyPersistObject is the C extension type used as a mixin for
   persistent objects defined in Python.  It extends the slots defined
   by PyPersist_HEAD with a po_dict used to provide __dict__.  The
   dict is needed for Python instances, but is unnecessary for objects
   like BTrees.
*/

#define PyPersist_HEAD \
    PyObject_HEAD \
    PyObject *po_dm; \
    PyObject *po_oid; \
    int po_atime; \
    enum PyPersist_State po_state;

typedef struct {
    PyPersist_HEAD
} PyPersistObject;

extern int _PyPersist_Load(PyPersistObject *);
extern int _PyPersist_RegisterDataManager(PyPersistObject *);
extern void _PyPersist_SetATime(PyPersistObject *);

/* A struct to encapsulation the PyPersist C API for use by other
   dynamically load extensions.
*/

typedef struct {
    PyTypeObject *base_type;
    int (*load)(PyPersistObject *);
    int (*reg_mgr)(PyPersistObject *);
    void (*set_atime)(PyPersistObject *);
} PyPersist_C_API_struct;

