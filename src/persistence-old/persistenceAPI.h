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
 
/* The PyPersist_C_API provides access to types and functions defined in
   the persistence extension module to other extension modules.  On some
   (all?) platforms, it isn't possible to have static references to
   functions and objects defined in other dynamically loaded modules.  The
   PyPersist_C_API defines a collection of pointers to the shared functions
   that can be initialized when a module is loaded.
*/

static PyPersist_C_API_struct *PyPersist_C_API;

#define PyPersist_TYPE PyPersist_C_API->base_type

#define PyPersist_INCREF(O) \
    if (((O)->po_state == UPTODATE) \
	|| ((O)->po_state == GHOST \
	    && PyPersist_C_API->load((PyPersistObject *)(O)))) \
	(O)->po_state = STICKY;

#define PyPersist_DECREF(O) \
    { \
        if ((O)->po_state == STICKY) \
	    (O)->po_state = UPTODATE; \
    }

/* XXX need to check *either* sticky or changed for now */
#define PyPersist_IS_STICKY(O) \
    ((O)->po_state == STICKY || (O)->po_state == CHANGED)

#define PyPersist_CHANGED(O) 				\
    (PyPersist_C_API->reg_mgr((PyPersistObject *)(O)) ?	\
     ((PyPersistObject *)(O))->po_state = CHANGED, 1 : 0)

#define PyPersist_SetATime(O) \
    PyPersist_C_API->set_atime((PyPersistObject *)(O))

/* Macros for compatibility with ZODB 3 C extensions. */

#define PER_USE_OR_RETURN(O, R) 				\
{								\
    if ((O)->po_state == GHOST) {				\
	if (!PyPersist_C_API->load((PyPersistObject *)(O)))	\
	    return (R);						\
	(O)->po_state = STICKY;					\
    } else if ((O)->po_state == UPTODATE) 			\
	(O)->po_state = STICKY;					\
}

#define PER_CHANGED(O) \
        PyPersist_C_API->reg_mgr((PyPersistObject *)(O)) ? -1 : 0

#define PER_ALLOW_DEACTIVATION(O) \
{ \
    if ((O)->po_state == STICKY) \
	(O)->po_state = UPTODATE; \
}

#define PER_PREVENT_DEACTIVATION(O) \
{ \
    if ((O)->po_state == UPTODATE) \
	(O)->po_state = STICKY; \
}

/* Macro to load object and mark sticky as needed.

   If the object is in the UPTODATE state, the mark it sticky.
   If the object is in the GHOST state, load it and mark it sticky.
 */

#define PER_USE(O) 						\
    (((PyPersistObject *)(O))->po_state != GHOST ?		\
     (((PyPersistObject *)(O))->po_state == UPTODATE ?		\
      ((PyPersistObject *)(O))->po_state = STICKY, 1 : 1) :	\
     (PyPersist_C_API->load((PyPersistObject *)(O)) ?		\
      ((PyPersistObject *)(O))->po_state = STICKY, 1 : 0))

#define PER_ACCESSED(O) PyPersist_C_API->set_atime((PyPersistObject *)O)
