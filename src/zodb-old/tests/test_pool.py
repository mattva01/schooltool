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
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Test the pool size logic in the database."""

import threading
import time
import unittest

from zodb.db import DB
from zodb.storage.mapping import MappingStorage

class Counter:

    def __init__(self):
        self._count = 0
        self._lock = threading.Lock()

    def inc(self):
        self._lock.acquire()
        try:
            self._count += 1
        finally:
            self._lock.release()

    def get(self):
        self._lock.acquire()
        try:
            return self._count
        finally:
            self._lock.release()

class ConnectThread(threading.Thread):

    def __init__(self, db, start_counter, open_counter, close_event):
        threading.Thread.__init__(self)
        self._db = db
        self._start = start_counter
        self._open = open_counter
        self._close = close_event

    def run(self):
        self._start.inc()
        cn = self._db.open()
        self._open.inc()
        cn.root()
        self._close.wait()
        cn.close()

class PoolTest(unittest.TestCase):

    def setUp(self):
        self.close = threading.Event()
        self.db = DB(MappingStorage(), pool_size=7)
        self.threads = []

    def tearDown(self):
        self.close.set()
        for t in self.threads:
            t.join()

    def testPoolLimit(self):
        # The default limit is 7, so try it with 10 threads.
        started = Counter()
        opened = Counter()
        for i in range(10):
            t = ConnectThread(self.db, started, opened, self.close)
            t.start()
            self.threads.append(t)

        # It's hard to get the thread synchronization right, but
        # this seems like it will sometimes do the right thing.

        # Wait for all the threads to call open().  It's possible
        # that a thread has started but not yet called open.
        for i in range(10):
            if started.get() < 10:
                time.sleep(0.1)
            else:
                break
        else:
            if started.get() < 10:
                self.fail("Only started %d threads out of 10" % started.get())

        # Now make sure that only 7 of the 10 threads opened.
        for i in range(10):
            if opened.get() < 7:
                time.sleep(0.1)
            else:
                break
        else:
            if opened.get() != 7:
                self.fail("Expected 7 threads to open, %d did" % opened.get())

        self.close.set()

        # Now make sure the last three get opened
        for i in range(10):
            if opened.get() < 10:
                time.sleep(0.1)
            else:
                break
        else:
            if opened.get() != 10:
                self.fail("Expected 10 threads to open, %d did" % opened.get())

def test_suite():
    return unittest.makeSuite(PoolTest)
