##############################################################################
#
# Copyright (c) 2002 Zope Corporation and Contributors.
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

from zope.interface import implements

from transaction import set_factory
from transaction.txn import Transaction as BaseTransaction

from zodb.interfaces import ITransaction, ITransactionAttrs

class Transaction(BaseTransaction):

    implements(ITransaction, ITransactionAttrs)

    user = ""
    description = ""
    _extension = None

    def __init__(self, manager=None, parent=None,
                 user=None, description=None):
        super(Transaction, self).__init__(manager, parent)
        if user is not None:
            self.user = user
        if description is not None:
            self.description = description

    def note(self, text):
        if self.description:
            self.description = "%s\n\n%s" % (self.description, text)
        else:
            self.description = text

    def setUser(self, user_name):
        self.user = "%s" % (user_name)

    def setExtendedInfo(self, name, value):
        if self._extension is None:
            self._extension = {}
        self._extension[name] = value

set_factory(Transaction)
