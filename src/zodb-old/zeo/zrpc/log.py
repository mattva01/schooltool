##############################################################################
#
# Copyright (c) 2001, 2002 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE
#
##############################################################################
import os
import threading
import logging

LOG_THREAD_ID = 0 # Set this to 1 during heavy debugging

_label = "zrpc:%s" % os.getpid()

# The code duplication here is for speed (save a layer of function call).

def critical(msg, *args, **kw):
    label = _label
    if LOG_THREAD_ID:
        label = "%s:%s" % (label, threading.currentThread().getName())
    logging.critical("%s: "+msg, label, *args, **kw)

def error(msg, *args, **kw):
    label = _label
    if LOG_THREAD_ID:
        label = "%s:%s" % (label, threading.currentThread().getName())
    logging.error("%s: "+msg, label, *args, **kw)

def warn(msg, *args, **kw):
    label = _label
    if LOG_THREAD_ID:
        label = "%s:%s" % (label, threading.currentThread().getName())
    logging.warn("%s: "+msg, label, *args, **kw)

def info(msg, *args, **kw):
    label = _label
    if LOG_THREAD_ID:
        label = "%s:%s" % (label, threading.currentThread().getName())
    logging.info("%s: "+msg, label, *args, **kw)

def debug(msg, *args, **kw):
    label = _label
    if LOG_THREAD_ID:
        label = "%s:%s" % (label, threading.currentThread().getName())
    logging.debug("%s: "+msg, label, *args, **kw)

REPR_LIMIT = 40

def short_repr(obj):
    "Return an object repr limited to REPR_LIMIT bytes."

    # Some of the objects being repr'd are large strings.  It's wastes
    # a lot of memory to repr them and then truncate, so special case
    # them in this function.
    # Also handle short repr of a tuple containing a long string.

    # This strategy works well for arguments to StorageServer methods.
    # The oid is usually first and will get included in its entirety.
    # The pickle is near the beginning, too, and you can often fit the
    # module name in the pickle.

    if isinstance(obj, str):
        if len(obj) > REPR_LIMIT:
            r = repr(obj[:REPR_LIMIT])
        else:
            r = repr(obj)
        if len(r) > REPR_LIMIT:
            r = r[:REPR_LIMIT-4] + '...' + r[-1]
        return r
    elif isinstance(obj, tuple):
        elts = []
        size = 0
        for elt in obj:
            r = repr(elt)
            elts.append(r)
            size += len(r)
            if size > REPR_LIMIT:
                break
        r = "(%s)" % (", ".join(elts))
    else:
        r = repr(obj)
    if len(r) > REPR_LIMIT:
        return r[:REPR_LIMIT] + '...'
    else:
        return r
