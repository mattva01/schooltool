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
"""A simple benchmark of creating and indexing email messages.

The benchmark loads and indexes a set of email messages from a Unix
mailbox.  The sender, subject, and message-id are used as index keys.
The benchmark commits every %(COMMIT_INTERVAL)d messages and reads at
most %(MAX)d messages from the mailbox.  At the end of the test run,
it packs the storage.  (The periodic packs on the way, along with the
index updates, will generate many data records that can be packed.)

It prints a one-line summary of its activities.

500 100 11.81 2253868 2084414

The columns are:
   - number of messages read
   - commit interval
   - elapsed CPU time
   - size of file before pack
   - size of file after pack
"""

import email
import mailbox
import os
import stat
import sys
import time

from persistence import Persistent
from persistence.dict import PersistentDict

from transaction import get_transaction

from zodb.db import DB
from zodb.storage.file import FileStorage
from zodb.btrees.OOBTree import OOBTree, OOSet

COMMIT_INTERVAL = 200
MAX = 5000

class Mailbox(Persistent):

    def __init__(self):
        self.messages = OOBTree()
        self.subjects = OOBTree()
        self.senders = OOBTree()
        self.size = 0

    def __len__(self):
        return self.size

    def add(self, msg):
        self.messages[msg.msgid] = msg
        if msg.sender:
            set = self.senders.get(msg.sender)
            if set is None:
                set = self.senders[msg.sender] = OOSet()
            set.insert(msg)
        if msg.subject:
            set = self.subjects.get(msg.subject)
            if set is None:
                set = self.subjects[msg.subject] = OOSet()
            set.insert(msg)
        self.size += 1

class Message(Persistent):

    def __init__(self, sender, recipients, subject, msgid, headers, payload):
        self.sender = sender
        self.recipients = recipients
        self.subject = subject
        if msgid is None:
            msgid = "%s %s" % (time.ctime(), id(self))
        self.msgid = msgid
        self.headers = headers
        self.payload = payload

    def __cmp__(self, msg):
        # The headers and payload must be the same, but start with
        # a simple check of the msgid.
        x = cmp(self.msgid, msg.msgid)
        if x:
            return x
        x = cmp(self.headers, msg.headers)
        if x:
            return x
        return cmp(self.payload, msg.payload)

    def fromEmail(cls, msg):
        recipients = []
        for h in "to", "cc", "bcc":
            v = msg.get(h)
            if v is not None:
                recipients.append(v)
        headers = PersistentDict()
        headers.update(msg)
        return cls(msg.get("from"), recipients, msg.get("subject"),
                   msg.get("message-id"), headers, msg.get_payload())

    fromEmail = classmethod(fromEmail)

def main(path):
    f = open(path, "rb")

    fs = FileStorage("emailbench.fs", create=True)
    db = DB(fs)
    cn = db.open()
    root = cn.root()
    mbox = root["mailbox"] = Mailbox()
    get_transaction().commit()

    factory = mailbox.UnixMailbox(f, email.message_from_file)
    while 1:
        raw = factory.next()
        if raw is None:
            break
        msg = Message.fromEmail(raw)
        mbox.add(msg)
        if len(mbox) % COMMIT_INTERVAL == 0:
            get_transaction().commit()

        if len(mbox) >= MAX:
            break
    n = len(mbox)
    get_transaction().commit()
    fs.pack(time.time())
    db.close()
    return n

def size(path):
    return os.stat(path)[stat.ST_SIZE]

if __name__ == "__main__":
    path = sys.argv[1]
    t0 = time.clock()
    n = main(path)
    t1 = time.clock()
    print n, COMMIT_INTERVAL, t1 - t0, size("emailbench.fs.old"), \
          size("emailbench.fs")
