##############################################################################
#
# Copyright (c) 2002 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Schema convenience functions

$Id$
"""

def getFieldNames(schema):
    """Return a list of all the Field names in a schema.
    """
    from zope.schema.interfaces import IField
    return [name for name in schema if IField.providedBy(schema[name])]

def getFields(schema):
    """Return a dictionary containing all the Fields in a schema.
    """
    from zope.schema.interfaces import IField
    fields = {}
    for name in schema:
        attr = schema[name]
        if IField.providedBy(attr):
            fields[name] = attr
    return fields

def getFieldsInOrder(schema,
                     _fieldsorter=lambda x, y: cmp(x[1].order, y[1].order)):
    """Return a list of (name, value) tuples in native schema order.
    """
    fields = getFields(schema).items()
    fields.sort(_fieldsorter)
    return fields

def getFieldNamesInOrder(schema):
    """Return a list of all the Field names in a schema in schema order.
    """
    return [ name for name, field in getFieldsInOrder(schema) ]
