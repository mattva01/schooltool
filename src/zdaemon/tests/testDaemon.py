# This file contains unit tests and a simple script that is explicitly
# invoked by the tests.  The script block goes first so that I don't
# have to bother getting the imports right.

# The script just kills itself or exits in a variety of ways.
import os
import sys

if __name__ == "__main__":
    arg = sys.argv[1]
    if arg == "signal":
        import signal
        os.kill(os.getpid(), signal.SIGKILL)
    elif arg == "exit":
        os._exit(2)
    os._exit(0)

# The rest is unittest stuff that can be run by testrunner.py.

import logging
import unittest
import zdaemon
import zdaemon.tests
import zdaemon.Daemon

class TestDoneError(RuntimeError):
    pass

class TestErrorHandler(logging.Handler):

    def emit(self, record):
        if record.levelno >= logging.ERROR:
            raise TestDoneError(self.format(record))

class DaemonTest(unittest.TestCase):

    dir, file = os.path.split(zdaemon.tests.__file__)
    script = os.path.join(dir, "testDaemon.py")

    def setUp(self):
        self.handler = TestErrorHandler()
        self.old_handlers = logging.root.handlers
        logging.root.handlers = []
        logging.root.addHandler(self.handler)
        self.level = logging.root.level # is there a better way?
        logging.root.setLevel(logging.ERROR)
        os.environ["Z_DEBUG_MODE"] = ""
        if os.environ.has_key("ZDAEMON_MANAGED"):
            del os.environ["ZDAEMON_MANAGED"]

    def tearDown(self):
        logging.root.removeHandler(self.handler)
        logging.root.handlers = self.old_handlers
        logging.root.setLevel(self.level)

    def run(self, arg):
        try:
            zdaemon.Daemon.run((self.script, arg))
        except SystemExit:
            pass

    def testDeathBySignal(self):
        try:
            self.run("signal")
        except TestDoneError, msg:
            self.assert_(str(msg).find("terminated by signal") != -1)
        else:
            self.fail("signal was not caught")

    def testDeathByExit(self):
        try:
            self.run("exit")
        except TestDoneError, msg:
            self.assert_(str(msg).find("exit status") != -1)
        else:
            self.fail("exit didn't raise an exception")

def test_suite():
    if hasattr(os, 'setsid'):
        return unittest.makeSuite(DaemonTest)
    else:
        return None
