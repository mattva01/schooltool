##############################################################################
#
# Copyright (c) 2003 Zope Corporation and Contributors.
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
"""Common helper classes for testing."""

import threading
from zodb.zeo.client import ClientStorage

class TestClientStorage(ClientStorage):

    def verify_cache(self, stub):
        self.end_verify = threading.Event()
        self.verify_result = super(TestClientStorage, self).verify_cache(stub)

    def endVerify(self):
        super(TestClientStorage, self).endVerify()
        self.end_verify.set()

class DummyDB:
    def invalidate(self, *args, **kws):
        pass


