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
# FOR A PARTICULAR PURPOSE
#
##############################################################################

"""Provide a mixin base class for Berkeley storage tests.
"""

from zodb.storage.tests import base

class MinimalTestBase(base.BerkeleyTestBase):
    from zodb.storage.bdbminimal import BDBMinimalStorage
    ConcreteStorage = BDBMinimalStorage


class FullTestBase(base.BerkeleyTestBase):
    from zodb.storage.bdbfull import BDBFullStorage
    ConcreteStorage = BDBFullStorage
