/*****************************************************************************

 Copyright (c) 2003 Zope Corporation and Contributors.
 All Rights Reserved.

 This software is subject to the provisions of the Zope Public License,
 Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
 THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
 WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
 WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
 FOR A PARTICULAR PURPOSE.

 *****************************************************************************/
 

#include "Python.h"
#include "structmember.h"

static PyObject *str___provides__, *str___implements__, *str___class__;
static PyObject *str___dict__, *str___signature__, *str_flattened;
static PyObject *_implements_reg, *classImplements, *proxySig, *oldSpecSig;
static PyObject *combinedSpec, *str_extends, *declarations;
static PyObject *str___providedBy__, *str_only;

#define TYPE(O) ((PyTypeObject*)(O))
#define OBJECT(O) ((PyObject*)(O))
#define CLASSIC(O) ((PyClassObject*)(O))

typedef struct {
  PyObject_HEAD
  PyObject *__signature__;
} ISB;

static void
ISB_dealloc(ISB *self)
{
  Py_XDECREF(self->__signature__);
  self->ob_type->tp_free((PyObject*)self);
}

static PyMemberDef ISB_members[] = {
  { "__signature__", T_OBJECT_EX, offsetof(ISB, __signature__), 0 },
  {NULL}	/* Sentinel */
};

static char ISBtype__doc__[] = 
"InterfaceSpecification base class that provides a __signature__ slot"
;

static PyTypeObject ISBType = {
	PyObject_HEAD_INIT(NULL)
	/* ob_size           */ 0,
	/* tp_name           */ "zope.interface._zope_interface_ospec."
                                "InterfaceSpecificationBase",
	/* tp_basicsize      */ sizeof(ISB),
	/* tp_itemsize       */ 0,
	/* tp_dealloc        */ (destructor)ISB_dealloc,
	/* tp_print          */ (printfunc)0,
	/* tp_getattr        */ (getattrfunc)0,
	/* tp_setattr        */ (setattrfunc)0,
	/* tp_compare        */ (cmpfunc)0,
	/* tp_repr           */ (reprfunc)0,
	/* tp_as_number      */ 0,
	/* tp_as_sequence    */ 0,
	/* tp_as_mapping     */ 0,
	/* tp_hash           */ (hashfunc)0,
	/* tp_call           */ (ternaryfunc)0,
	/* tp_str            */ (reprfunc)0,
        /* tp_getattro       */ (getattrofunc)0,
        /* tp_setattro       */ (setattrofunc)0,
        /* tp_as_buffer      */ 0,
        /* tp_flags          */ Py_TPFLAGS_DEFAULT 
                                | Py_TPFLAGS_BASETYPE
                                ,
	/* tp_doc            */ ISBtype__doc__,
        /* tp_traverse       */ (traverseproc)0,
        /* tp_clear          */ (inquiry)0,
        /* tp_richcompare    */ (richcmpfunc)0,
        /* tp_weaklistoffset */ (long)0,
        /* tp_iter           */ (getiterfunc)0,
        /* tp_iternext       */ (iternextfunc)0,
        /* tp_methods        */ 0,
        /* tp_members        */ ISB_members,
        /* tp_getset         */ 0,
        /* tp_base           */ 0,
        /* tp_dict           */ 0, /* internal use */
        /* tp_descr_get      */ (descrgetfunc)0,
        /* tp_descr_set      */ (descrsetfunc)0,
        /* tp_dictoffset     */ 0,
        /* tp_init           */ (initproc)0,
        /* tp_alloc          */ (allocfunc)0,
        /* tp_new            */ (newfunc)0 /*PyType_GenericNew*/,
};

typedef struct {
  PyObject_HEAD
  PyObject *provides;
  PyObject *cls;
  PyObject *spec;
} OSpec;

static PyTypeObject OSpecType;

static int
OSpec_init(OSpec *self, PyObject *args, PyObject *kwds)
{
	static char *kwlist[] = {"provides", "cls", NULL};
        PyObject *provides, *cls;

        if (! PyArg_ParseTupleAndKeywords(args, kwds, "OO", kwlist, 
                                          &provides, &cls))
        	return -1; 

        Py_INCREF(provides);
        self->provides = provides;
        Py_INCREF(cls);
        self->cls = cls;

        return 0;
}

static int
OSpec_traverse(OSpec *self, visitproc visit, void *arg)
{
  if (self->provides != Py_None && visit(self->provides, arg) < 0)
    return -1;
  if (visit(self->cls, arg) < 0)
    return -1;
  if (self->spec && visit(self->spec, arg) < 0)
    return -1;
  return 0;
}

static int
OSpec_clear(OSpec *self)
{
  Py_XDECREF(self->provides);
  Py_XDECREF(self->cls);
  Py_XDECREF(self->spec);
  return 0;
}

static void
OSpec_dealloc(OSpec *self)
{
  PyObject_GC_UnTrack((PyObject *) self);
  OSpec_clear(self);
  self->ob_type->tp_free((PyObject*)self);
}

static PyObject *
getsig(PyObject *spec, PyObject *cls)
{
  PyObject *sig;

  if (PyObject_TypeCheck(spec, &ISBType))
    {
      sig = ((ISB*)spec)->__signature__;
      if (sig == NULL)
        {
          PyErr_SetString(PyExc_TypeError, 
                          "Specification has no __signature__");
          return NULL;
        }
      Py_INCREF(sig);
    }
  else
    { /* Wrong type of specification */
      if (cls == NULL)
        {

          /* This isn't the right kind of thing. Check for a
             __signature__ anyway. */

          sig = PyObject_GetAttr(spec, str___signature__);
        }
      else
        /* Maybe it's an old style declaration */
        sig = PyObject_CallFunctionObjArgs(oldSpecSig, cls, spec, NULL);
    }

  return sig;
}

static PyObject *
OSpec_getsig(OSpec *self, void *closure)
{
  PyObject *provides, *psig=0, *cls, *key, *dict, *implements, *sig=0, *result;

  provides = self->provides;
  if (provides != Py_None)
    {
      psig = getsig(provides, NULL);
      if (psig == NULL)
        return NULL;
    }

  /* Own: psig */

  cls = self->cls;

  /* Own: psig, cls */

  /* Ultimately, we get the implementation spec from a dict with some
     key, where the dict is normally the class dict and the key is
     normally '__implements__'. */

  key = str___implements__;
  
  if (PyClass_Check(cls))
    {
      dict = CLASSIC(cls)->cl_dict;
      Py_INCREF(dict);
    }
  else if (PyType_Check(cls))
    {
      if (TYPE(cls)->tp_flags & Py_TPFLAGS_HEAPTYPE)
        dict = TYPE(cls)->tp_dict;
      else
        {
          dict = _implements_reg;
          key = cls;
        }
      Py_INCREF(dict);
    }
  else
    dict = PyObject_GetAttr(cls, str___dict__);

  /* Own: psig, dict */

  if (dict == NULL)
    {
      /* We couldn't get a dict. Must be a proxy */
      PyErr_Clear();
      sig = PyObject_CallFunctionObjArgs(proxySig, cls, NULL);
    }
  else
    {
      if (! PyDict_Check(dict))
        {
          PyErr_SetObject(PyExc_TypeError, dict); 
          return NULL;
        }
      implements = PyDict_GetItem(dict, key);
      if (implements == NULL)
        {
          result = PyObject_CallFunctionObjArgs(classImplements, cls, NULL);
          if (result != NULL)
            {
              Py_DECREF(result);
              implements = PyDict_GetItem(dict, key);
              if (implements == NULL)
                PyErr_SetObject(PyExc_KeyError, key); 
            }
        }

      if (implements != NULL)
        sig = getsig(implements, cls);
      
      Py_DECREF(dict);
    }

  /* Own: psig */


  if (sig == NULL)
    {
      Py_XDECREF(psig);
      return NULL;
    }

  if (psig != NULL && ! PyObject_IsTrue(psig))
    {
      Py_DECREF(psig);
      psig = NULL;
    }

  if (sig != NULL && ! PyObject_IsTrue(sig))
    {
      Py_DECREF(sig);
      sig = NULL;
    }

  if (sig != NULL)
    if (psig != NULL)
      {
        result = PyTuple_New(2);
        if (result == NULL)
          {
            Py_DECREF(psig);
            Py_DECREF(sig);
            return NULL;
          }
        PyTuple_SET_ITEM(result, 0, psig);
        PyTuple_SET_ITEM(result, 1, sig);
        return result;
      }
    else
      return sig;
  else if (psig != NULL)
    return psig;
  else
    return PyString_FromString("");
}    

static PyGetSetDef OSpec_getset[] = {
    {"__signature__", 
     (getter)OSpec_getsig, (setter)0,
     "Specification signature",
     NULL},
    {NULL}  /* Sentinel */
};

static PyObject *
getspec(OSpec *self)
{
  if (self->spec == NULL)
    self->spec = PyObject_CallFunctionObjArgs(combinedSpec, 
                                              self->provides, self->cls,
                                              NULL);
  return self->spec;
}

static PyObject *
OSpec_add(PyObject *v, PyObject *w)
{
  if (PyObject_TypeCheck(v, &OSpecType))
    {
      v = getspec((OSpec*)v);
      if (v == NULL) 
        return NULL;
    }
  else if (PyObject_TypeCheck(w, &OSpecType))
    {
      w = getspec((OSpec*)w);
      if (w == NULL) 
        return NULL;
    }
  else
    {
      PyErr_SetString(PyExc_TypeError, "Invalid types for add");
    }

  return PyNumber_Add(v, w);
}

static PyObject *
OSpec_sub(PyObject *v, PyObject *w)
{
  if (PyObject_TypeCheck(v, &OSpecType))
    {
      v = getspec((OSpec*)v);
      if (v == NULL) 
        return NULL;
    }
  else if (PyObject_TypeCheck(w, &OSpecType))
    {
      w = getspec((OSpec*)w);
      if (w == NULL) 
        return NULL;
    }
  else
    {
      PyErr_SetString(PyExc_TypeError, "Invalid types for subtract");
    }

  return PyNumber_Subtract(v, w);
}

static int
OSpec_nonzero(OSpec *self)
{
  return PyObject_IsTrue(getspec(self));
}

static PyNumberMethods OSpec_as_number = {
    /* nb_add                  */ (binaryfunc)OSpec_add,
    /* nb_subtract             */ (binaryfunc)OSpec_sub,
    /* nb_multiply to nb_absolute */ 0, 0, 0, 0, 0, 0, 0, 0, 
    /* nb_nonzero             */ (inquiry)OSpec_nonzero,
};

static int
OSpec_contains(OSpec *self, PyObject *v)
{
  PyObject *spec;

  spec = getspec(self);
  if (spec == NULL)
    return -1;

  return PySequence_In(spec, v);
}


static PySequenceMethods OSpec_as_sequence = {
	/* sq_length         */ 0,
	/* sq_concat         */ 0,
	/* sq_repeat         */ 0,
	/* sq_item           */ 0,
	/* sq_slice          */ 0,
	/* sq_ass_item       */ 0,
	/* sq_ass_slice      */ 0,
	/* sq_contains       */ (objobjproc)OSpec_contains,
};

static PyObject *
OSpec_iter(OSpec *self)
{
  PyObject *spec;

  spec = getspec(self);
  if (spec == NULL)
    return NULL;

  return PyObject_GetIter(spec);
}

static PyObject *
OSpec_flattened(OSpec *self)
{
  PyObject *spec;

  spec = getspec(self);
  if (spec == NULL)
    return NULL;

  return PyObject_CallMethodObjArgs(spec, str_flattened, NULL);
}

static PyObject *
OSpec_extends(OSpec *self, PyObject *other)
{
  PyObject *spec;

  spec = getspec(self);
  if (spec == NULL)
    return NULL;

  return PyObject_CallMethodObjArgs(spec, str_extends, other, NULL);
}


static struct PyMethodDef OSpec_methods[] = {
	{"flattened",	(PyCFunction)OSpec_flattened,	METH_NOARGS, ""},
	{"extends",	(PyCFunction)OSpec_extends,	METH_O, ""},
	{NULL,		NULL}		/* sentinel */
};


static char OSpecType__doc__[] = 
"Base type for object specifications computed via descriptors (no wrappers)"
;

static PyTypeObject OSpecType = {
	PyObject_HEAD_INIT(NULL)
	/* ob_size           */ 0,
	/* tp_name           */ "zope.interface._zope_interface_ospec."
                                "ObjectSpecification",
	/* tp_basicsize      */ sizeof(OSpec),
	/* tp_itemsize       */ 0,
	/* tp_dealloc        */ (destructor)OSpec_dealloc,
	/* tp_print          */ (printfunc)0,
	/* tp_getattr        */ (getattrfunc)0,
	/* tp_setattr        */ (setattrfunc)0,
	/* tp_compare        */ (cmpfunc)0,
	/* tp_repr           */ (reprfunc)0,
	/* tp_as_number      */ &OSpec_as_number,
	/* tp_as_sequence    */ &OSpec_as_sequence,
	/* tp_as_mapping     */ 0,
	/* tp_hash           */ (hashfunc)0,
	/* tp_call           */ (ternaryfunc)0,
	/* tp_str            */ (reprfunc)0,
        /* tp_getattro       */ (getattrofunc)0,
        /* tp_setattro       */ (setattrofunc)0,
        /* tp_as_buffer      */ 0,
        /* tp_flags          */ Py_TPFLAGS_DEFAULT
                                | Py_TPFLAGS_BASETYPE
                                | Py_TPFLAGS_CHECKTYPES
                                | Py_TPFLAGS_HAVE_GC
                                ,
	/* tp_doc            */ OSpecType__doc__,
        /* tp_traverse       */ (traverseproc)OSpec_traverse,
        /* tp_clear          */ (inquiry)OSpec_clear,
        /* tp_richcompare    */ (richcmpfunc)0,
        /* tp_weaklistoffset */ (long)0,
        /* tp_iter           */ (getiterfunc)OSpec_iter,
        /* tp_iternext       */ (iternextfunc)0,
        /* tp_methods        */ OSpec_methods,
        /* tp_members        */ 0,
        /* tp_getset         */ OSpec_getset,
        /* tp_base           */ 0,
        /* tp_dict           */ 0, /* internal use */
        /* tp_descr_get      */ (descrgetfunc)0,
        /* tp_descr_set      */ (descrsetfunc)0,
        /* tp_dictoffset     */ 0,
        /* tp_init           */ (initproc)OSpec_init,
        /* tp_alloc          */ (allocfunc)0,
        /* tp_new            */ (newfunc)0 /*PyType_GenericNew*/,
};

static PyObject *
getObjectSpecification(PyObject *ignored, PyObject *ob)
{
  PyObject *provides, *cls, *result;
  static PyObject *empty = NULL;

  provides = PyObject_GetAttr(ob, str___provides__);
  if (provides == NULL)
    PyErr_Clear();

  cls = PyObject_GetAttr(ob, str___class__);
  if (cls == NULL)
    {
      PyErr_Clear();
      if (provides == NULL)
        {
          if (empty == NULL)
            {
              empty = PyObject_GetAttrString(declarations, "_empty");
              if (empty == NULL)
                return NULL;
            }
          Py_INCREF(empty);
          return empty;
        }
      return provides;
    }

  if (provides == NULL)
    {
      Py_INCREF(Py_None);
      provides = Py_None;
    }
  
  result = PyObject_CallFunctionObjArgs(OBJECT(&OSpecType), provides, cls, 
                                        NULL);
  Py_DECREF(provides);
  Py_DECREF(cls);

  return result;
}

static PyObject *
providedBy(PyObject *ignored, PyObject *ob)
{
  PyObject *result;
  
  result = PyObject_GetAttr(ob, str___providedBy__);
  if (result != NULL)
    {
      /* We want to make sure we have a spec. We can't do a type check
         because we may have a proxy, so we'll just try to get the
         only attribute.
      */
      ignored = PyObject_GetAttr(result, str_only);
      if (ignored == NULL)
        PyErr_Clear();
      else
        {
          Py_DECREF(ignored);
          return result;
        }
    }

  PyErr_Clear();

  return getObjectSpecification(NULL, ob);
}

typedef struct {
  PyObject_HEAD
} OSpecDescr;

static PyObject *
OSpecDescr_descr_get(PyObject *self, PyObject *inst, PyObject *cls)
{
  if (inst == NULL)
    inst = cls;

  return getObjectSpecification(NULL, inst);
}

static PyTypeObject OSpecDescrType = {
	PyObject_HEAD_INIT(NULL)
	/* ob_size           */ 0,
	/* tp_name           */ "zope.interface._zope_interface_ospec."
                                "ObjectSpecificationDescriptor",
	/* tp_basicsize      */ sizeof(OSpecDescr),
	
        /* tp_itemsize to tp_as_buffer */ 
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,

        /* tp_flags          */ Py_TPFLAGS_DEFAULT
				| Py_TPFLAGS_BASETYPE ,
	/* tp_doc            */ "ObjectSpecification descriptor",
        
        /* tp_traverse to tp_dict */
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,

        /* tp_descr_get      */ (descrgetfunc)OSpecDescr_descr_get,
};

int
init_globals(void)
{
  str___implements__ = PyString_FromString("__implements__");
  if (str___implements__ == NULL)
    return -1;
  
  str___provides__ = PyString_FromString("__provides__");
  if (str___provides__ == NULL)
    return -1;
  
  str___providedBy__ = PyString_FromString("__providedBy__");
  if (str___providedBy__ == NULL)
    return -1;
  
  str___class__ = PyString_FromString("__class__");
  if (str___class__ == NULL)
    return -1;
  
  str___dict__ = PyString_FromString("__dict__");
  if (str___dict__ == NULL)
    return -1;
  
  str___signature__ = PyString_FromString("__signature__");
  if (str___signature__ == NULL)
    return -1;
  
  str_flattened = PyString_FromString("flattened");
  if (str_flattened == NULL)
    return -1;
  
  str_extends = PyString_FromString("extends");
  if (str_extends == NULL)
    return -1;
  
  str_only = PyString_FromString("only");
  if (str_only == NULL)
    return -1;
  
  _implements_reg = PyDict_New();
  if (_implements_reg == NULL)
    return -1;

  return 0;
}

int
init_declarations(void)
{
  declarations = PyImport_ImportModule("zope.interface.declarations");
  if (declarations == NULL)
    return -1;

  classImplements = PyObject_GetAttrString(declarations, "classImplements");
  if (classImplements == NULL)
    return -1;

  proxySig = PyObject_GetAttrString(declarations, "proxySig");
  if (proxySig == NULL)
    return -1;

  oldSpecSig = PyObject_GetAttrString(declarations, "oldSpecSig");
  if (oldSpecSig == NULL)
    return -1;

  combinedSpec = PyObject_GetAttrString(declarations, "combinedSpec");
  if (combinedSpec == NULL)
    return -1;
  return 0;
}

static struct PyMethodDef module_methods[] = {
	{"getObjectSpecification",  (PyCFunction)getObjectSpecification,
         METH_O, "internal function to compute an object spec"},
	{"providedBy",  (PyCFunction)providedBy, METH_O, 
         "Return a specification for the interfaces of an object"},
	{NULL,	 (PyCFunction)NULL, 0, NULL}		/* sentinel */
};

static char _zope_interface_ospec_module_documentation[] = 
"C implementation of parts of zope.interface.declarations"
;

#ifndef PyMODINIT_FUNC	/* declarations for DLL import/export */
#define PyMODINIT_FUNC void
#endif
PyMODINIT_FUNC
init_zope_interface_ospec(void)
{
  PyObject *module;

  /* Initialize types: */  

  ISBType.tp_new = PyType_GenericNew;
  if (PyType_Ready(&ISBType) < 0)
    return;


  OSpecType.tp_new = PyType_GenericNew;
  OSpecType.tp_free = _PyObject_GC_Del;
  if (PyType_Ready(&OSpecType) < 0)
    return;
  if (OSpecType.tp_dict && 
      PyMapping_SetItemString(OSpecType.tp_dict, "only", Py_True) < 0
      )
    return;

 
  OSpecDescrType.tp_new = PyType_GenericNew;
  if (PyType_Ready(&OSpecDescrType) < 0)
    return;

  if (init_globals() < 0)
    return;
  
  /* Create the module and add the functions */
  module = Py_InitModule3("_zope_interface_ospec", module_methods,
                          _zope_interface_ospec_module_documentation);
  
  if (module == NULL)
    return;

  /* Add types: */
  if (PyModule_AddObject(module, "InterfaceSpecificationBase", 
                         (PyObject *)&ISBType) < 0)
    return;

  if (PyModule_AddObject(module, "ObjectSpecification", 
                         (PyObject *)&OSpecType) < 0)
    return;

  if (PyModule_AddObject(module, "ObjectSpecificationDescriptor", 
                         (PyObject *)&OSpecDescrType) < 0)
    return;

  if (PyModule_AddObject(module, "_implements_reg", _implements_reg) < 0)
    return;

  /* init_declarations() loads objects from zope.interface.declarations,
     which circularly depends on the objects defined in this module.
     Call init_declarations() last to ensure that the necessary names
     are bound.
  */
  init_declarations();
}

