
#define VALUEMACROS_H "$Id: objectvaluemacros.h,v 1.2 2002/12/25 14:12:16 jim Exp $\n"

#define VALUE_TYPE PyObject *
#define VALUE_TYPE_IS_PYOBJECT
#define TEST_VALUE(VALUE, TARGET) PyObject_Compare((VALUE),(TARGET))
#define INCREF_VALUE(k) Py_INCREF(k)
#define DECREF_VALUE(k) Py_DECREF(k)
#define COPY_VALUE(k,e) k=(e)
#define COPY_VALUE_TO_OBJECT(O, K) O=(K); Py_INCREF(O)
#define COPY_VALUE_FROM_ARG(TARGET, ARG, S) TARGET=(ARG)
#define NORMALIZE_VALUE(V, MIN) Py_INCREF(V)
