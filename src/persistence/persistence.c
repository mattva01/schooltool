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
 
#include "Python.h"
#include <assert.h>
#include "structmember.h"
#include "persistence.h"


static char PyPersist_doc_string[] =
"Defines Persistent mixin class for persistent objects.\n"
"\n"
"$Id: persistence.c,v 1.20 2003/07/03 19:12:56 jeremy Exp $\n";

/* A custom metaclass is only needed to support Python 2.2. */
#if PY_MAJOR_VERSION == 2 && PY_MINOR_VERSION == 2
static PyTypeObject PyPersist_MetaType;
#else
#define PyPersist_MetaType PyType_Type
#endif

/* Python version of the simple_new function; */
static PyObject *py_simple_new = NULL;

/* A helper function that registers a persistent object with its data
   manager.
*/

static PyObject *s_register = NULL;

int
_PyPersist_RegisterDataManager(PyPersistObject *self) 
{
    PyObject *meth, *arg, *result;

    if (!self->po_dm)
	return 1;
    /* If the object is in the CHANGED state, then it is already registered. */
    if (self->po_state == CHANGED)
	return 1;
    if (!s_register)
	s_register = PyString_InternFromString("register");
    meth = PyObject_GetAttr((PyObject *)self->po_dm, s_register);
    if (meth == NULL)
	return 0;
    arg = PyTuple_New(1);
    if (!arg) {
	Py_DECREF(meth);
	return 0;
    }
    Py_INCREF(self);
    PyTuple_SET_ITEM(arg, 0, (PyObject *)self);
    result = PyObject_Call(meth, arg, NULL);
    Py_DECREF(arg);
    Py_DECREF(meth);
    if (result) {
	if (self->po_state == UPTODATE || self->po_state == STICKY)
	    self->po_state = CHANGED;
	Py_DECREF(result);
	return 1;
    } else
	return 0;
}

/* A helper function that loads an object's state from its data manager.
*/

int
_PyPersist_Load(PyPersistObject *self) 
{
    static PyObject *s_setstate = NULL;
    PyObject *meth, *arg, *result;
    enum PyPersist_State state;

    if (self->po_dm == NULL)
	return 0;
    if (s_setstate == NULL) 
	s_setstate = PyString_InternFromString("setstate");
    meth = PyObject_GetAttr((PyObject *)self->po_dm, s_setstate);
    if (meth == NULL)
	return 0;

    arg = PyTuple_New(1);
    if (arg == NULL) {
	Py_DECREF(meth);
	return 0;
    }
    Py_INCREF(self);
    PyTuple_SET_ITEM(arg, 0, (PyObject *)self);

    /* set state to CHANGED while setstate() call is in progress
       to prevent a recursive call to _PyPersist_Load().
    */
    state = self->po_state;
    self->po_state = CHANGED;
    result = PyObject_Call(meth, arg, NULL);
    self->po_state = state;

    Py_DECREF(arg);
    Py_DECREF(meth);

    if (result) {
	Py_DECREF(result);
	return 1;
    }
    else 
	return 0;
}

/* A helper function to set the atime from the current time.  The
   po_atime slot stores seconds since the start of the day.  The need
   for an atime slot and its particular semantics are specific to the
   current cache implementation.

   XXX The calls to time() are very expensive.
 */

void
_PyPersist_SetATime(PyPersistObject *self)
{
    time_t t = time(NULL);
    self->po_atime = t % 86400;
}

static PyObject *
persist_getstate(PyObject *self)
{
    PyObject **pdict = _PyObject_GetDictPtr(self);
    PyObject *state, *k, *v;
    int pos = 0;

    /* XXX UPDATE_STATE_IF_NECESSARY */

    /* This instance has no dict. */
    if (!pdict) {
	/* XXX check for slots */
	Py_INCREF(Py_None);
	return Py_None;
    }

    state = PyDict_New();
    if (state == NULL)
	return NULL;

    /* This instance never initialized its dict. */
    if ((*pdict) == NULL)
	return state;

    while (PyDict_Next(*pdict, &pos, &k, &v)) {
	if (PyString_Check(k)) {
	    char *attrname = PyString_AS_STRING(k);
	    if (strncmp(attrname, "_v_", 3) == 0)
		continue;
	    /* XXX Should I ignore _p_ too? */
	    if (strncmp(attrname, "_p_", 3) == 0)
		continue;
	}
	if (PyDict_SetItem(state, k, v) < 0) {
	    Py_DECREF(state);
	    return NULL;
	}
    }
    return state;
}

/* XXX What's the contract of __setstate__() if the object already has
   state?  Should it update the state or should it replace the state?
   A call to __setstate__() seems most likely intended to replace the
   old state with a new state, so clear first.
*/

static PyObject *
persist_setstate(PyObject *self, PyObject *state)
{
    PyObject **pdict;
    PyObject *dict;
    PyObject *k, *v;
    PyObject *serial = NULL;
    static PyObject *_p_serial;
    int pos = 0;

    if (state == Py_None) {
	Py_INCREF(Py_None);
	return Py_None;
    }

    pdict = _PyObject_GetDictPtr(self);
    assert(pdict); /* not sure if this can return NULL */
    if ((*pdict) == NULL) {
	*pdict = PyDict_New();
	if ((*pdict) == NULL)
	    return NULL;
    }
    else {
	if (!_p_serial) {
	    _p_serial = PyString_InternFromString("_p_serial");
	}
	serial = PyDict_GetItem(*pdict, _p_serial);
	Py_XINCREF(serial);
	PyDict_Clear(*pdict);
    }
    dict = *pdict;
    
    if (!PyDict_Check(state)) {
	PyErr_SetString(PyExc_TypeError, "state must be a dictionary");
	return NULL;
    }

    while (PyDict_Next(state, &pos, &k, &v)) {
	if (PyString_Check(k)) {
	    char *attrname = PyString_AS_STRING(k);
	    if (strncmp(attrname, "_p_", 3) == 0)
		continue;
	}
	if (PyDict_SetItem(dict, k, v) < 0)
	    return NULL;
    }
    if (serial) {
	if (PyDict_SetItem(*pdict, _p_serial, serial) < 0)
	    return NULL;
	Py_DECREF(serial);
    }

    Py_INCREF(Py_None);
    return Py_None;
}

/* Only activate an object if it is a ghost. */

static PyObject *
persist_activate(PyPersistObject *self)
{
    if (self->po_state == GHOST && self->po_dm) {
	if (!_PyPersist_Load((PyPersistObject *)self))
	    return NULL;
	self->po_state = UPTODATE;
    }
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject *
persist_deactivate(PyPersistObject *self, PyObject *args, PyObject *keywords)
{
    int ghostify = 1;
    PyObject *force = NULL;

    if (args && PyTuple_GET_SIZE(args) > 0) {
	PyErr_SetString(PyExc_TypeError, 
			"_p_deactivate takes not positional arguments");
	return NULL;
    }
    if (keywords) {
	int size = PyDict_Size(keywords);
	force = PyDict_GetItemString(keywords, "force");
	if (force)
	    size--;
	if (size) {
	    PyErr_SetString(PyExc_TypeError, 
			    "_p_deactivate only accepts keyword arg force");
	    return NULL;
	}
    }

    if (self->po_dm && self->po_oid) {
	ghostify = self->po_state == UPTODATE;
	if (!ghostify && force) {
	    if (PyObject_IsTrue(force))
		ghostify = 1;
	    if (PyErr_Occurred())
		return NULL;
	}
	if (ghostify) {
	    PyObject **pdict = _PyObject_GetDictPtr((PyObject *)self);
	    if (pdict && *pdict) {
		Py_DECREF(*pdict);
		*pdict = NULL;
	    }
	    self->po_state = GHOST;
	}
    }

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject *
persist_get_state(PyPersistObject *self)
{
    if (self->po_state == GHOST) {
	Py_INCREF(Py_None);
	return Py_None;
    }
    return PyInt_FromLong(self->po_state);
}

static int
call_p_deactivate(PyPersistObject *self, int unraisable)
{
    static PyObject *t = NULL;
    PyObject *func, *r;
    if (!t) {
	t = PyTuple_New(0);
	if (!t)
	    return 0;
    }
    func = PyObject_GetAttrString((PyObject *)self, "_p_deactivate");
    if (!func)
	return 0;
    r = PyObject_Call(func, t, NULL);
    if (unraisable && !r) {
	PyErr_WriteUnraisable(func);
    }
    Py_DECREF(func);
    if (!r)
	return 0;
    else {
	Py_DECREF(r);
	return 1;
    }
}

#define CHANGED_NONE 0
#define CHANGED_FALSE 1
#define CHANGED_TRUE 2

static int
persist_set_state(PyPersistObject *self, PyObject *v)
{
    int newstate, bool;

    if (!v) {
	PyErr_SetString(PyExc_TypeError, "can't delete _p_changed");
	return -1;
    }
    
    /* If the object isn't registered with a data manager, setting its
       state is meaningless.
     */
    if (!self->po_dm || !self->po_oid)
	return 0;

    bool = PyObject_IsTrue(v);
    if (PyErr_Occurred())
	return -1;
    newstate = bool ? CHANGED_TRUE : CHANGED_FALSE;

    if (self->po_state == GHOST) 
	/* If the object is a ghost, it makes no sense to try to mark
	   it as changed.  It's state must be loaded first.

	   XXX Should it raise an exception?  It doesn't in ZODB3.
	*/
	return 0;
    else if (newstate == CHANGED_TRUE) {
	/* Mark an up-to-date object as changed. */
	if (self->po_state == UPTODATE) {
	    if (!_PyPersist_RegisterDataManager((PyPersistObject *)self))
		return -1;
	    self->po_state = CHANGED;
	}
    } else if (newstate == CHANGED_FALSE) {
	/* Mark a changed object as up-to-date, but do nothing if it's
	   already up-to-date or ghostified.
	 */
	if (self->po_state == CHANGED || self->po_state == STICKY)
	    self->po_state = UPTODATE;
    } else if (self->po_state == UPTODATE) {
	/* The final case is for CHANGED_NONE, which is only
	   meaningful when the object is already in the up-to-date state. 
	   In this case, turn the object into a ghost.
	*/
	if (!call_p_deactivate(self, 0))
	    return -1;
    }

    return 0;
}

/* convert_name() returns a new reference to a string name
   or sets an exception and returns NULL.
*/

static PyObject *
convert_name(PyObject *name)
{
#ifdef Py_USING_UNICODE
    /* The Unicode to string conversion is done here because the
       existing tp_setattro slots expect a string object as name
       and we wouldn't want to break those. */
    if (PyUnicode_Check(name)) {
	name = PyUnicode_AsEncodedString(name, NULL, NULL);
    }
    else
#endif
    if (!PyString_Check(name)) {
	PyErr_SetString(PyExc_TypeError, "attribute name must be a string");
	return NULL;
    } else
	Py_INCREF(name);
    return name;
}

/* The crucial methods for a persistent object are the tp_getattr and
   tp_setattr hooks, which allow the persistence machinery to
   automatically detect changes to and accesses of the object's state.

   In general, if getattr() is called on a ghost, the data manager
   must load the ghost's state before calling PyObject_GenericGetAttr().
   There are several special attributes that ignore this rule.

   The current implemenation probably isn't right, because it doesn't
   even attempt to deal with a persistent classes that defines its own
   __getattr__ or __getattribute__.  
*/

/* Returns true if the object requires unghostification.

   Don't unghostify for any attribute starting with _p_.  The Python
   special names __del__, __dict__, and __class__ are also exempt.
*/

static int
persist_check_getattr(const char *s)
{
    if (*s++ != '_')
	return 1;
    if (*s == 'p') {
	s++;
	if (*s == '_')  
	    return 0; /* _p_ */
	else
	    return 1; 
    }
    else if (*s == '_') {
	s++;
	switch (*s) {
	case 'd':
	    s++;
	    if (!strcmp(s, "ict__"))
		return 0; /* __dict__ */
	    if (!strcmp(s, "el__"))
		return 0; /* __del__ */
	    return 1;
	case 'c':
	    return strcmp(s, "class__");
	case 's':
	    return strcmp(s, "setstate__");
	default:
	    return 1;
	}
    }
    return 1;
}

static PyObject *
persist_getattro(PyPersistObject *self, PyObject *name)
{
    PyObject *attr;
    char *s_name;

    name = convert_name(name);
    if (!name)
	return NULL;
    s_name = PyString_AS_STRING(name);
    /* If any attribute other than an _p_ attribute or __dict__ is
       accessed, make sure that the object state is loaded.  

       Implement with simple check on s_name[0] to avoid two strncmp()
       calls for all attribute names that don't start with an
       underscore.
    */

    if (persist_check_getattr(s_name)) {
	if (self->po_state == GHOST) {
	    /* Prevent the object from being registered as changed.

	       If the object is changed while it is being unghostified,
	       it should not be registered with the data manager as
	       a changed object.  The easiest way to prevent this is
	       to mark it as already changed, which implies it is
	       already registered. 
	    */
	    self->po_state = CHANGED;
	    if (!_PyPersist_Load((PyPersistObject *)self)) {
		/* What if an error occured in _p_deactivate()?

		   It's not clear what we should do here.  The code is
		   obviously ignoring the exception, but it shouldn't
		   return 0 for a getattr and set an exception.  The
		   simplest change is to clear the exception, but that
		   simply masks the error. 

		   The second argument to call_p_deactivate() says
		   to print the exception to stderr. It would probably be
		   better to log it but that would be painful from C.
		*/
                Py_DECREF(name);
		if (!call_p_deactivate(self, 1))
		    return NULL;
		self->po_state = GHOST;
		return NULL;
	    } else
		self->po_state = UPTODATE;
	}
	_PyPersist_SetATime((PyPersistObject *)self);
    }

    /* will invoke an __getattr__ if it exists. */
    attr = PyObject_GenericGetAttr((PyObject *)self, name);
    Py_DECREF(name);
    return attr;
}

/* persist_setattr_setup() will load the object's state if necessary.
   Return values:

   -1 : error occurred, exception set
   0 : state not loaded, attribute name is _p_*, _v_*, or __dict__
   1 : state loaded, attribute name is normal
*/

/* Returns true if the object state must be loaded in setattr.

   If any attribute other than _p_*, _v_*, or __dict__ is set,
   the object must be unghostified.
*/

static int
persist_check_setattr(const char *s)
{
    assert(s && *s);
    if (*s++ != '_')
	return 1;
    switch (*s++) {
    case 'p':
    case 'v':
	return *s != '_';
	break;
    case '_':
	return strcmp(s, "dict__");
	break;
    default:
	return 1;
    }
}

static int
persist_setattr_prep(PyPersistObject *self, PyObject *name, PyObject *value)
{
    char *s_name;

    assert(PyString_Check(name));
    s_name = PyString_AS_STRING(name);

    /* XXX What will go wrong if someone assigns to an _p_ or _v_
       attribute and we have no state loaded?  Is it safe?
       The current setstate implementation will not delete old values 
       and excludes _p_ and _v_ attributes from the pickle.
    */

    if (persist_check_setattr(s_name)) {
	if (self->po_state == GHOST) {
	    if (self->po_dm == NULL || self->po_oid == NULL) {
		PyErr_SetString(PyExc_TypeError,
				"attempt to modify unrevivable ghost");
		return -1;
	    }
	    if (!_PyPersist_Load((PyPersistObject *)self))
		return -1;
	    self->po_state = UPTODATE;
	}
	/* If the object is marked as UPTODATE then it must be
	   registered as modified.  If it was just unghosted, it
	   will be in the UPTODATE state.  

	   If it's in the changed state, it should already be registered.
	   
	   XXX What if it's in the sticky state?

	   XXX It looks like these two cases could be collapsed somehow.
	*/
	if (self->po_state == UPTODATE && self->po_dm &&
	    !_PyPersist_RegisterDataManager((PyPersistObject *)self))
	    return -1;

	if (self->po_dm && self->po_oid) {
	    self->po_state = CHANGED;
	    _PyPersist_SetATime((PyPersistObject *)self);
	}
	return 1;
    }
    return 0;
}

static int
persist_setattro(PyPersistObject *self, PyObject *name, PyObject *value)
{
    int r;

    name = convert_name(name);
    if (!name)
	return -1;
    if (persist_setattr_prep(self, name, value) < 0) {
        Py_DECREF(name);
	return -1;
    }
    r = PyObject_GenericSetAttr((PyObject *)self, name, value);
    Py_DECREF(name);

    return r;
}

static PyObject *
persist_p_set_or_delattr(PyPersistObject *self, PyObject *name,
                         PyObject *value)
{
    PyObject *res;
    int r;

    name = convert_name(name);
    if (!name)
	return NULL;
    r = persist_setattr_prep(self, name, value);
    if (r < 0) {
        Py_DECREF(name);
	return NULL;
    }
    else if (r > 0)
	res = Py_False;
    else {
	/* r == 0 implies the name is _p_, _v_, or __dict__,
	   and that we should handle it.
	*/
	res = Py_True;
	r = PyObject_GenericSetAttr((PyObject *)self, name, value);
	if (r < 0) {
            Py_DECREF(name);
	    return NULL;
        }
    }
    Py_INCREF(res);
    Py_DECREF(name);
    return res;
}

/* Exported as _p_setattr() 

   Returns True if the internal persistence machinery handled the setattr.
   Returns False if it did not.
*/

static PyObject *
persist_p_setattr(PyPersistObject *self, PyObject *args)
{
    PyObject *name, *value;

    if (!PyArg_ParseTuple(args, "OO:_p_setattr", &name, &value))
	return NULL;

    return persist_p_set_or_delattr(self, name, value);
}

/* Exported as _p_delattr() 

   Returns True if the internal persistence machinery handled the setattr.
   Returns False if it did not.
*/

static PyObject *
persist_p_delattr(PyPersistObject *self, PyObject *name)
{
    return persist_p_set_or_delattr(self, name, NULL);
}

static void
persist_dealloc(PyPersistObject *self)
{
    Py_XDECREF(self->po_dm);
    Py_XDECREF(self->po_oid);
    PyObject_GC_Del(self);
}

static int
persist_traverse(PyPersistObject *self, visitproc visit, void *arg)
{
    int err;

#define VISIT(SLOT) \
    if (SLOT) { \
	err = visit((PyObject *)(SLOT), arg); \
	if (err) \
		     return err; \
    }
    VISIT(self->po_dm);
    VISIT(self->po_oid);
#undef VISIT
    return 0;
}

static int
persist_clear(PyPersistObject *self)
{
    Py_XDECREF(self->po_dm);
    Py_XDECREF(self->po_oid);
    self->po_dm = NULL;
    self->po_oid = NULL;
    return 0;
}

static PyObject *
persist_reduce(PyPersistObject *self)
{
    PyObject *state, *args=NULL, *result, *__getstate__;

    static PyObject *__getstate__str = NULL;
  
    if (! __getstate__str) {
	__getstate__str = PyString_InternFromString("__getstate__");
	if (! __getstate__str)
	    return NULL; 
    }
  
    __getstate__ = PyObject_GetAttr((PyObject*)self, __getstate__str);
    if (! __getstate__)
	return NULL;

    state = PyObject_CallObject(__getstate__, NULL);
    Py_DECREF(__getstate__);
    if (! state)
	return NULL;
  
    args = PyTuple_New(1);
    if (! args)
	goto err;
  
    Py_INCREF(self->ob_type);
    PyTuple_SET_ITEM(args, 0, (PyObject *)self->ob_type);
  
    result = PyTuple_New(3);
    if (! result)
	goto err;
  
    Py_INCREF(py_simple_new);
    PyTuple_SET_ITEM(result, 0, py_simple_new);
    PyTuple_SET_ITEM(result, 1, args);
    PyTuple_SET_ITEM(result, 2, state);
  
    return result;      
  
 err:
    Py_DECREF(state);
    Py_XDECREF(args);
    return NULL;
}

static PyMethodDef persist_methods[] = {
    {"__reduce__", (PyCFunction)persist_reduce, METH_NOARGS, },
    {"__getstate__", (PyCFunction)persist_getstate, METH_NOARGS, },
    {"__setstate__", persist_setstate, METH_O, },
    {"_p_activate", (PyCFunction)persist_activate, METH_NOARGS, },
    {"_p_deactivate", (PyCFunction)persist_deactivate, METH_KEYWORDS, },
    {"_p_setattr", (PyCFunction)persist_p_setattr, METH_VARARGS, },
    {"_p_delattr", (PyCFunction)persist_p_delattr, METH_O, },
    {NULL}
};

static PyGetSetDef persist_getsets[] = {
    {"_p_changed", (getter)persist_get_state, (setter)persist_set_state},
    {NULL}
};

/* XXX should any of these be read-only? */

static PyMemberDef persist_members[] = {
    {"_p_jar", T_OBJECT, offsetof(PyPersistObject, po_dm)},
    {"_p_oid", T_OBJECT, offsetof(PyPersistObject, po_oid)},
    {"_p_atime", T_INT, offsetof(PyPersistObject, po_atime)},
    {"_p_state", T_INT, offsetof(PyPersistObject, po_state), RO},
    {NULL}
};

/* This module is compiled as a shared library.  Some compilers don't
   allow addresses of Python objects defined in other libraries to be
   used in static initializers here.  The DEFERRED_ADDRESS macro is
   used to tag the slots where such addresses appear; the module init
   function must fill in the tagged slots at runtime.  The argument is
   for documentation -- the macro ignores it.
*/
#define DEFERRED_ADDRESS(ADDR) 0

static PyTypeObject PyPersist_Type = {
    PyObject_HEAD_INIT(DEFERRED_ADDRESS(&PyPersist_MetaType))
    0,					/* ob_size */
    "persistence.Persistent",		/* tp_name */
    sizeof(PyPersistObject),		/* tp_basicsize */
    0,					/* tp_itemsize */
    (destructor)persist_dealloc,	/* tp_dealloc */
    0,					/* tp_print */
    0,					/* tp_getattr */
    0,					/* tp_setattr */
    0,					/* tp_compare */
    0,					/* tp_repr */
    0,					/* tp_as_number */
    0,					/* tp_as_sequence */
    0,					/* tp_as_mapping */
    0,					/* tp_hash */
    0,					/* tp_call */
    0,					/* tp_str */
    (getattrofunc)persist_getattro,	/* tp_getattro */
    (setattrofunc)persist_setattro,	/* tp_setattro */
    0,					/* tp_as_buffer */
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_HAVE_GC |
    Py_TPFLAGS_BASETYPE, 		/* tp_flags */
    0,					/* tp_doc */
    (traverseproc)persist_traverse,	/* tp_traverse */
    (inquiry)persist_clear,		/* tp_clear */
    0,					/* tp_richcompare */
    0,					/* tp_weaklistoffset */
    0,					/* tp_iter */
    0,					/* tp_iternext */
    persist_methods,			/* tp_methods */
    persist_members,			/* tp_members */
    persist_getsets,			/* tp_getset */
    0,					/* tp_base */
    0,					/* tp_dict */
    0,					/* tp_descr_get */
    0,					/* tp_descr_set */
    0, 					/* tp_dictoffset */
    0,					/* tp_init */
    0,					/* tp_alloc */
    0,					/* tp_new */
};

#if PY_MAJOR_VERSION == 2 && PY_MINOR_VERSION == 2

/* PyPersist_MetaType / PersistentMetaClass exists to work around
   problems with the way Python 2.2 determines whether a class's
   instances will get an __dict__, or, more concretely, what the value
   of tp_dictoffset should be.  The problem is that types with a
   custom tp_setattro field are not given an __dict__.  The work-around
   requires a metaclass.

   The metaclass uses a custom tp_alloc function PyPersist_Alloc() to
   set tp_dictoffset to -1.  This assignment prevents type_new() from
   doing anything with dictoffset.  Later the metaclass tp_new
   function PyPersist_New() assigns a reasonable value for
   tp_dictoffset and creates an __dict__ descriptor.
*/

static PyObject *
persist_dict(PyObject *obj, void *context)
{
    PyObject **dictptr;

    dictptr = _PyObject_GetDictPtr(obj);
    assert(dictptr);
    
    if (!*dictptr) {
	PyObject *dict = PyDict_New();
	if (!dict)
	    return NULL;
	*dictptr = dict;
    }
    Py_INCREF(*dictptr);
    return *dictptr;
}

static PyGetSetDef persist_meta_getsets[] = {
	{"__dict__",  (getter)persist_dict,  NULL, NULL},
	{NULL}
};

static PyObject *
PyPersist_Alloc(PyTypeObject *metatype, int nitems)
{
    PyObject *type = PyType_GenericAlloc(metatype, nitems);
    ((PyTypeObject *)type)->tp_dictoffset = -1;
    return type;
}

static PyObject *
PyPersist_New(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    PyTypeObject *new;
    PyObject *descr;

    new = (PyTypeObject *)PyType_Type.tp_new(type, args, kwds);
    if (!new)
	return NULL;

    /* If a base class already defined a dictoffset, use that. */
    new->tp_dictoffset = new->tp_base->tp_dictoffset;

    /* It is possible for a class that inherits from Persistent to
       define __slots__, in which case it shouldn't have a dict.
       We have to look in the dictionary supplied to the keyword arguments,
       however, or we can be fooled by a base type having __slots__.
       (See 'persistence.tests.test_persistence.Test.testSlots')
    */
    if (PyMapping_HasKeyString(PyTuple_GetItem(args,2), "__slots__")) {
	return (PyObject *)new;
    }

    if (!new->tp_dictoffset) {
	/* Update the type to know about __dict__. */
	if (new->tp_itemsize)
	    new->tp_dictoffset = -(long)sizeof(PyObject *);
	else if (new->tp_weaklistoffset && !new->tp_base->tp_weaklistoffset) {
	    /* Python expects the weaklistoffset to come before the
	       dictoffset.  The order matters to extra_ivars(), which
	       is involved in determining the best base class.
	    */
	    new->tp_dictoffset = new->tp_weaklistoffset;
	    new->tp_weaklistoffset = new->tp_basicsize;
	}
	else
	    /* XXX Should be aligned properly */
	    new->tp_dictoffset = new->tp_basicsize;
	new->tp_basicsize += sizeof(PyObject *);

	/* Put a descriptor for __dict__ in the type's __dict__.
	   It's too late to get type to do this for us. */
	descr = PyDescr_NewGetSet(new, persist_meta_getsets);
	if (!descr) {
	    Py_DECREF(new);
	    return NULL;
	}
	if (PyDict_SetItemString(new->tp_dict, "__dict__", descr) < 0) {
	    Py_DECREF(new);
	    return NULL;
	}
	Py_DECREF(descr);
    }

    return (PyObject *)new;
}

static PyTypeObject PyPersist_MetaType = {
    PyObject_HEAD_INIT(DEFERRED_ADDRESS(&PyType_Type))
    0,					/* ob_size */
    "persistence.PersistentMetaClass",	/* tp_name */
};

#endif

static PyObject *
simple_new(PyObject *self, PyObject *type_object)
{
    return PyType_GenericNew((PyTypeObject*)type_object, NULL, NULL);
}

static PyMethodDef PyPersist_methods[] = {
    {"simple_new", simple_new, METH_O,
     "Create an object by simply calling a class' __new__ method without "
     "arguments."},
    {NULL, NULL}
};

static PyPersist_C_API_struct c_api = {
    &PyPersist_Type,
    _PyPersist_Load,
    _PyPersist_RegisterDataManager,
    _PyPersist_SetATime
};

static int
persist_set_interface(PyTypeObject *type)
{
    PyObject *mod = NULL, *iface = NULL, *implements = NULL;
    int r = -1;

    mod = PyImport_ImportModule("persistence.interfaces");
    if (mod == NULL)
	goto err;
    iface = PyObject_GetAttrString(mod, "IPersistent");
    if (iface == NULL)
	goto err;
    implements = PyTuple_New(1);
    if (implements == NULL) 
	goto err;
    Py_INCREF(iface);
    PyTuple_SET_ITEM(implements, 0, iface);
    assert(type->tp_dict != NULL);
    r = PyDict_SetItemString(type->tp_dict, "__implements__", implements);
 err:
    Py_XDECREF(mod);
    Py_XDECREF(iface);
    Py_XDECREF(implements);
    return r;
}

static int 
insenum(PyObject *d, char *key, enum PyPersist_State val)
{
    PyObject *n = PyInt_FromLong(val);
    int success = 1;
    if (n == NULL)
	return 0;
    if (PyDict_SetItemString(d, key, n) < 0)
	success = 0;
    Py_DECREF(n);
    return success;
}

void 
init_persistence(void)
{
    PyObject *m, *d, *v;

    m = Py_InitModule3("_persistence",
                       PyPersist_methods, PyPersist_doc_string);
    if (m == NULL)
	return;
    d = PyModule_GetDict(m);
    if (d == NULL)
	return;

#if PY_MAJOR_VERSION == 2 && PY_MINOR_VERSION == 2
    PyPersist_MetaType.ob_type = &PyType_Type;
    PyPersist_MetaType.tp_alloc = PyPersist_Alloc;
    PyPersist_MetaType.tp_new = PyPersist_New;
    PyPersist_MetaType.tp_base = &PyType_Type;
    PyPersist_MetaType.tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_HAVE_GC |
	Py_TPFLAGS_BASETYPE;
    PyPersist_MetaType.tp_traverse = PyType_Type.tp_traverse;
    PyPersist_MetaType.tp_clear = PyType_Type.tp_clear;
    if (PyType_Ready(&PyPersist_MetaType) < 0)
	return;

    /* Cheap hack to force us to be used instead of 'type' as '__base__';
       this ensures that we are always used for C-level layout, and can
       therefore interoperate with other (pure Python) metaclasses.
       (See 'persistence.tests.test_persistence.Test.testMultipleMeta')
       This costs us a (PyObject *) per subclass of Persistent, but it
       seems to be the only way to fix this in Python 2.2.x.  :(
    */
    PyPersist_MetaType.tp_basicsize += sizeof(PyObject *);

    Py_INCREF(&PyPersist_MetaType);
    if (PyDict_SetItemString(d, "PersistentMetaClass", 
			     (PyObject *)&PyPersist_MetaType) < 0)
	return;
#else
    Py_INCREF(&PyType_Type);
    if (PyDict_SetItemString(d, "PersistentMetaClass", 
			     (PyObject *)&PyType_Type) < 0)
	return;
#endif

    PyPersist_Type.ob_type = &PyPersist_MetaType;
    PyPersist_Type.tp_new = PyType_GenericNew;
    if (PyType_Ready(&PyPersist_Type) < 0)
	return;
    if (persist_set_interface(&PyPersist_Type) < 0)
	return;

    Py_INCREF(&PyPersist_Type);
    if (PyDict_SetItemString(d, "Persistent", (PyObject *)&PyPersist_Type) < 0)
	return;

    v = PyCObject_FromVoidPtr(&c_api, NULL);
    if (v == NULL)
	return;
    if (PyDict_SetItemString(d, "C_API", v) < 0)
	return;
    Py_DECREF(v);

    if (!insenum(d, "UPTODATE", UPTODATE))
	return;
    if (!insenum(d, "CHANGED", CHANGED))
	return;
    if (!insenum(d, "STICKY", STICKY))
	return;
    if (!insenum(d, "GHOST", GHOST))
	return;

    py_simple_new = PyMapping_GetItemString(d, "simple_new");
    if (! py_simple_new)
        return;
}
