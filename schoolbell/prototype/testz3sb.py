#!/usr/bin/env python2.3
"""
Functionally test z3schoolbell.py
"""

import os
import sys
import httplib
import unittest
import time
import socket
from glob import glob
from doctesthttp import FunctionalDocFileSuite, doctest, HTTPCaller


class AppController:

    def start(self):
        self.http = HTTPCaller()
        self.start = not self.alive()
        if self.start:
            print "Starting the server..."
            os.system('python2.3 z3schoolbell.py &')

    def alive(self):
        s = httplib.HTTPConnection('localhost', 8080)
        try:
            s.connect()
        except socket.error:
            return False
        s.close()
        return True

    def wait_for_startup(self):
        print "Waiting for server...",
        for n in range(20):
            if self.alive():
                print "OK"
                return
            time.sleep(.5)
            sys.stdout.write(".")
            sys.stdout.flush()
        raise "Got bored"

    def reset(self):
        self.http("""GET /@@resetdb.html HTTP/1.1
Authorization: Basic mgr:mgrpw
""")

    def stop(self):
        if self.start:
            print "Stopping the server..."
            try:
                self.http("""POST /++etc++process/ServerControl.html HTTP/1.1
Authorization: Basic mgr:mgrpw
Content-Type: application/x-www-form-urlencoded
Content-Length: 20

shutdown=&time:int=0""")
            except httplib.BadStatusLine:
                print "OK"


def main():
    app = AppController()
    app.start()
    suite = unittest.TestSuite()
    for filename in glob('ftests/*.txt'):
        test = FunctionalDocFileSuite(filename,
                    setUp=lambda test: app.reset(),
                    optionflags=(doctest.ELLIPSIS |
                                 doctest.REPORT_NDIFF |
                                 doctest.REPORT_ONLY_FIRST_FAILURE |
                                 doctest.NORMALIZE_WHITESPACE))
        suite.addTest(test)
    app.wait_for_startup()
    unittest.TextTestRunner().run(suite)
    app.stop()


if __name__ == '__main__':
    main()
