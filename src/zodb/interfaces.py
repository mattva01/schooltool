##############################################################################
#
# Copyright (c) 2001 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""ZODB database interfaces and exceptions

The Zope Object Database (ZODB) manages persistent objects using
pickle-based object serialization.  The database has a pluggable
storage backend.

The IAppDatabase, IAppConnection, and ITransaction interfaces describe
the public APIs of the database.

The IDatabase, IConnection, and ITransactionAttrs interfaces describe
private APIs used by the implementation.

$Id: interfaces.py,v 1.19.4.1 2004/01/09 22:23:26 jim Exp $
"""

from ZODB.POSException import *
