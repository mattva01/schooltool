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
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
import time

from _timestamp import TimeStamp

def newTimeStamp(prev=None):
    ts = timeStampFromTime(time.time())
    if prev is not None:
        ts = ts.laterThan(prev)
    return ts

def timeStampFromTime(t):
    args = time.gmtime(t)[:5] + (t % 60,)
    return TimeStamp(*args)
