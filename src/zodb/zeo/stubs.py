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
"""RPC stubs for client and server interfaces."""

class ClientStorageStub:
    """An RPC stub class for the interface exported by ClientStorage.

    This is the interface presented by ClientStorage to the
    StorageServer; i.e. the StorageServer calls these methods and they
    are executed in the ClientStorage.

    See the ClientStorage class for documentation on these methods.

    It is currently important that all methods here are asynchronous
    (meaning they don't have a return value and the caller doesn't
    wait for them to complete), *and* that none of them cause any
    calls from the client to the storage.  This is due to limitations
    in the zrpc subpackage.

    The on-the-wire names of some of the methods don't match the
    Python method names.  That's because the on-the-wire protocol was
    fixed for ZEO 2 and we don't want to change it.  There are some
    aliases in ClientStorage.py to make up for this.
    """

    def __init__(self, rpc):
        """Constructor.

        The argument is a connection: an instance of the
        zrpc.connection.Connection class.
        """
        self.rpc = rpc

    def beginVerify(self):
        self.rpc.callAsync('beginVerify')

    def invalidateVerify(self, args):
        self.rpc.callAsync('invalidateVerify', args)

    def endVerify(self):
        self.rpc.callAsync('endVerify')

    def invalidateTransaction(self, tid, invlist):
        self.rpc.callAsyncNoPoll('invalidateTransaction', tid, invlist)

    def serialnos(self, arg):
        self.rpc.callAsync('serialnos', arg)

    def info(self, arg):
        self.rpc.callAsync('info', arg)

class StorageServerStub:
    """An RPC stub class for the interface exported by ClientStorage.

    This is the interface presented by the StorageServer to the
    ClientStorage; i.e. the ClientStorage calls these methods and they
    are executed in the StorageServer.

    See the StorageServer module for documentation on these methods,
    with the exception of _update(), which is documented here.
    """

    def __init__(self, rpc):
        """Constructor.

        The argument is a connection: an instance of the
        zrpc.connection.Connection class.
        """
        self.rpc = rpc

    def extensionMethod(self, name):
        return ExtensionMethodWrapper(self.rpc, name).call

    def _update(self):
        """Handle pending incoming messages.

        This method is typically only used when no asyncore mainloop
        is already active.  It can cause arbitrary callbacks from the
        server to the client to be handled.
        """
        self.rpc.pending()

    def register(self, storage_name, read_only):
        self.rpc.call('register', storage_name, read_only)

    def getVersion(self):
        return self.rpc.call('getVersion')

    def setVersion(self, version):
        self.rpc.callAsync('setVersion', version)

    def get_info(self):
        return self.rpc.call('get_info')

    def getAuthProtocol(self):
        return self.rpc.call('getAuthProtocol')
    
    def lastTransaction(self):
        return self.rpc.call('lastTransaction')

    def getInvalidations(self, tid):
        return self.rpc.call('getInvalidations', tid)

    def beginZeoVerify(self):
        self.rpc.callAsync('beginZeoVerify')

    def zeoVerify(self, oid, s, sv):
        self.rpc.callAsync('zeoVerify', oid, s, sv)

    def endZeoVerify(self):
        self.rpc.callAsync('endZeoVerify')

    def pack(self, t, wait=None):
        if wait is None:
            self.rpc.call('pack', t)
        else:
            self.rpc.call('pack', t, wait)

    def zeoLoad(self, oid):
        return self.rpc.call('zeoLoad', oid)

    def storea(self, oid, serial, data, refs, version, id):
        self.rpc.callAsync('storea', oid, serial, data, refs, version, id)

    def tpcBegin(self, id, user, descr, ext, tid, status):
        return self.rpc.call('tpcBegin', id, user, descr, ext, tid, status)

    def tpcVote(self, trans_id):
        return self.rpc.call('tpcVote', trans_id)

    def tpcFinish(self, id):
        return self.rpc.call('tpcFinish', id)

    def tpcAbort(self, id):
        self.rpc.callAsync('tpcAbort', id)

    def abortVersion(self, src, id):
        return self.rpc.call('abortVersion', src, id)

    def commitVersion(self, src, dest, id):
        return self.rpc.call('commitVersion', src, dest, id)

    def history(self, oid, version, length=None):
        if length is None:
            return self.rpc.call('history', oid, version)
        else:
            return self.rpc.call('history', oid, version, length)

    def load(self, oid, version):
        return self.rpc.call('load', oid, version)

    def loadSerial(self, oid, serial):
        return self.rpc.call('loadSerial', oid, serial)

    def getSerial(self, oid):
        return self.rpc.call('getSerial', oid)

    def modifiedInVersion(self, oid):
        return self.rpc.call('modifiedInVersion', oid)

    def newObjectIds(self, n=None):
        if n is None:
            return self.rpc.call('newObjectIds')
        else:
            return self.rpc.call('newObjectIds', n)

    def newObjectId(self, last=None):
        if last is None:
            return self.rpc.call('new_oid')
        else:
            return self.rpc.call('new_oid', last)

    def lastTransaction(self):
        return self.rpc.call('lastTransaction')

    def store(self, oid, serial, data, refs, version, trans):
        return self.rpc.call('store', oid, serial, data, refs, version, trans)

    def undo(self, trans_id, trans):
        return self.rpc.call('undo', trans_id, trans)

    def undoLog(self, first, last):
        return self.rpc.call('undoLog', first, last)

    def undoInfo(self, first, last, spec):
        return self.rpc.call('undoInfo', first, last, spec)

    def versionEmpty(self, vers):
        return self.rpc.call('versionEmpty', vers)

    def versions(self, max=None):
        if max is None:
            return self.rpc.call('versions')
        else:
            return self.rpc.call('versions', max)

class ExtensionMethodWrapper:
    def __init__(self, rpc, name):
        self.rpc = rpc
        self.name = name
        
    def call(self, *a, **kwa):
        return self.rpc.call(self.name, *a, **kwa)
