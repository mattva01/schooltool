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
"""Helper file used to launch a ZEO server cross platform"""

import os
import sys
import time
import errno
import getopt
import random
import socket
import logging
import asyncore
import threading

from zodb import config
import zodb.zeo.server
from zodb.zeo import threadedasync
from zodb.zeo.runzeo import ZEOOptions
from zodb.zeo.server import StorageServer

class ZEOTestServer(asyncore.dispatcher):
    """A server for killing the whole process at the end of a test.

    The first time we connect to this server, we write an ack character down
    the socket.  The other end should block on a recv() of the socket so it
    can guarantee the server has started up before continuing on.

    The second connect to the port immediately exits the process, via
    os._exit(), without writing data on the socket.  It does close and clean
    up the storage first.  The other end will get the empty string from its
    recv() which will be enough to tell it that the server has exited.

    I think this should prevent us from ever getting a legitimate addr-in-use
    error.
    """
    __super_init = asyncore.dispatcher.__init__

    def __init__(self, addr, server, keep):
        self.__super_init()
        self._sockets = [self]
        self._server = server
        self._keep = keep
        # Count down to zero, the number of connects
        self._count = 1
        # Create a logger
        self.logger = logging.getLogger('zeoserver.%d.%s' %
                                        (os.getpid(), addr))
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        # Some ZEO tests attempt a quick start of the server using the same
        # port so we have to set the reuse flag.
        self.set_reuse_addr()
        try:
            self.bind(addr)
        except:
            # We really want to see these exceptions
            import traceback
            traceback.print_exc()
            raise
        self.listen(5)
        self.logger.info('bound and listening')

    def handle_accept(self):
        sock, addr = self.accept()
        self.logger.info('in handle_accept()')
        # When we're done with everything, close the storage.  Do not write
        # the ack character until the storage is finished closing.
        if self._count <= 0:
            self.logger.info('closing the storage')
            self._server.close_server()
            if not self._keep:
                for storage in self._server.storages.values():
                    storage.cleanup()
            self.logger.info('exiting')
            # Close all the other sockets so that we don't have to wait
            # for os._exit() to get to it before starting the next
            # server process.
            for s in self._sockets:
                s.close()
            # Now explicitly close the socket returned from accept(),
            # since it didn't go through the wrapper.
            sock.close()
            os._exit(0)
        self.logger.info('continuing')
        sock.send('X')
        self._count -= 1

    def register_socket(self, sock):
        # Register a socket to be closed when server shutsdown.
        self._sockets.append(sock)
        

def main():
    # Initialize the logging module.
    import logging.config
    logging.basicConfig()
    level = os.getenv("LOGGING")
    if level:
        level = int(level)
    else:
        level = logging.CRITICAL
    logging.root.setLevel(level)
    logini = os.getenv("LOGINI")
    if logini:
        logging.config.fileConfig(logini)

    # Create a logger
    logger = logging.getLogger('zeoserver.%d' % os.getpid())
    logger.info('starting')

    # We don't do much sanity checking of the arguments, since if we get it
    # wrong, it's a bug in the test suite.
    keep = 0
    configfile = None
    # Parse the arguments and let getopt.error percolate
    opts, args = getopt.getopt(sys.argv[1:], 'kC:')
    for opt, arg in opts:
        if opt == '-k':
            keep = 1
        elif opt == '-C':
            configfile = arg

    zo = ZEOOptions()
    zo.realize(["-C", configfile])
    zeo_port = int(zo.address[1])
            
    # XXX a hack
    if zo.auth_protocol == "plaintext":
        import zodb.zeo.tests.auth_plaintext
        
    # Open the config file and let ZConfig parse the data there.  Then remove
    # the config file, otherwise we'll leave turds.
    # The rest of the args are hostname, portnum
    test_port = zeo_port + 1
    test_addr = ('localhost', test_port)
    addr = ('localhost', zeo_port)
    logger.info('creating the storage server')
    storage = zo.storages[0].open()
    mon_addr = None
    if zo.monitor_address:
        mon_addr = zo.monitor_address.address
    server = StorageServer(
        zo.address,
        {"1": storage},
        read_only=zo.read_only,
        invalidation_queue_size=zo.invalidation_queue_size,
        transaction_timeout=zo.transaction_timeout,
        monitor_address=mon_addr,
        auth_protocol=zo.auth_protocol,
        auth_filename=zo.auth_database,
        auth_realm=zo.auth_realm)

    try:
        logger.info('creating the test server, keep: %s', keep)
        t = ZEOTestServer(test_addr, server, keep)
    except socket.error, e:
        if e[0] <> errno.EADDRINUSE: raise
        logger.info('addr in use, closing and exiting')
        storage.close()
        storage.cleanup()
        sys.exit(2)
        
    logger.info('creating the storage server')
    t.register_socket(server.dispatcher)
    # Loop for socket events
    logger.info('entering threadedasync loop')
    threadedasync.loop()


if __name__ == '__main__':
    main()
