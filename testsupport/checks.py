#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003,2005 Shuttleworth Foundation
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
Checks for the unit tests.
"""

import sys
import sets
import logging

from schooltool.testing.test import name_of_test

__metaclass__ = type


def warn(msg):
    print >> sys.stderr, "\n" + msg


def sorted(l):
    l = list(l) # make a copy
    l.sort()
    return l


def difflist(old, new):
    """Show the differences between two lists."""
    import pprint
    import difflib
    old = pprint.pformat(old) + "\n"
    new = pprint.pformat(new) + "\n"
    return ''.join(difflib.unified_diff(old.splitlines(True),
                                        new.splitlines(True)))


class TransactionChecks:

    def startTest(self, test):
        import transaction
        txn = transaction.get()
        self.had_resources = bool(txn._resources)

    def stopTest(self, test):
        if self.had_resources:
            return
        import transaction
        txn = transaction.get()
        if txn._resources:
            warn("%s left an unclean transaction" % name_of_test(test))
            txn.abort()


class StdoutWrapper:

    def __init__(self, stm):
        self._stm = stm
        self.written = False

    def __getattr__(self, attr):
        return getattr(self._stm, attr)

    def write(self, *args):
        self.written = True
        self._stm.write(*args)


class StdoutChecks:

    def __init__(self):
        self.stdout_wrapper = StdoutWrapper(sys.stdout)
        self.stderr_wrapper = StdoutWrapper(sys.stderr)

    def startTest(self, test):
        import sys
        self.old_stdout = sys.stdout
        self.old_stderr = sys.stderr
        sys.stdout = self.stdout_wrapper
        sys.stderr = self.stderr_wrapper
        self.stdout_wrapper.written = False
        self.stderr_wrapper.written = False

        # readline is disabled in PDB when our stdout hook is found instead of
        # the real stdout.  This problem is fixed through a monkey patch on
        # pdb.set_trace() and pdb.post_mortem().

        import pdb

        def set_trace_hook():
            sys.stdout = self.old_stdout
            self.old_pdb_set_trace()
            sys.stdout = self.stdout_wrapper

        def post_mortem_hook(tb):
            sys.stdout = self.old_stdout
            self.old_pdb_post_mortem(tb)
            sys.stdout = self.stdout_wrapper

        self.old_pdb_set_trace = pdb.set_trace
        self.old_pdb_post_mortem = pdb.post_mortem
        pdb.set_trace = set_trace_hook
        pdb.post_mortem = post_mortem_hook

    def stopTest(self, test):
        import sys
        warn_stdout_replaced = sys.stdout is not self.stdout_wrapper
        warn_stderr_replaced = sys.stderr is not self.stderr_wrapper
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr
        if warn_stdout_replaced:
            warn("%s replaced sys.stdout" % name_of_test(test))
        if warn_stderr_replaced:
            warn("%s replaced sys.stderr" % name_of_test(test))
        if self.stdout_wrapper.written:
            warn("%s wrote to sys.stdout" % name_of_test(test))
        if self.stderr_wrapper.written:
            warn("%s wrote to sys.stderr" % name_of_test(test))

        import pdb
        pdb.set_trace = self.old_pdb_set_trace
        pdb.post_mortem = self.old_pdb_post_mortem


class LibxmlChecks:

    def __init__(self):
        self.last_mem = 0

    def startTest(self, test):
        import libxml2
        mem = libxml2.debugMemory(1)
        if mem > self.last_mem:
            warn("libxml2 used %d bytes of memory before test %s"
                 % (mem - self.last_mem, name_of_test(test)))

        # Attempts to call libxml2.cleanupParser() in stopTest and then check
        # that debugMemory() returns 0 were unsuccessful.  It appears that
        # cleanupParser can only work correctly once.  Instead try to subtract
        # this overhead once by calling libxml2.initParser() and remembering
        # the amount of memory it takes (395 bytes here).
        libxml2.initParser()
        self.last_mem = libxml2.debugMemory(1)
        if self.last_mem != libxml2.debugMemory(1):
            warn("libxml2 acts strangely")

    def stopTest(self, test):
        import libxml2
        # Using libxml2 after cleanupParser was called might be unsafe, even
        # though it appears to work just fine now. See
        # http://mail.gnome.org/archives/xml/2004-October/msg00099.html
        # I think catching memory leaks in the code is worth the risk of
        # calling cleanupParser in unit tests -- we do not do that in real
        # code.
        libxml2.cleanupParser()
        mem = libxml2.debugMemory(1)
        if mem > self.last_mem:
            warn("%s leaked %d bytes of memory in libxml2 objects (total: %d)"
                 % (test, mem - self.last_mem, mem))
        self.last_mem = mem

        # make libxml2 noisy, just in case someone used QuietLibxml2Mixin and
        # forgot to call tearDownLibxml2
        def on_error_callback(ctx, msg):
            sys.stderr.write(msg)
        libxml2.registerErrorHandler(on_error_callback, None)


class LoggingChecks:
    """Detect unit tests that fiddle with the logging package.

    This class looks for the following fiddlings:

      import logging
      logging.getLogger('foo').disabled = True
      logging.getLogger('foo').propagate = False
      logging.getLogger('foo').setLevel(bar)
      logging.getLogger('foo').addHandler(handler)
      logging.getLogger('foo').removeHandler(handler)
    """

    def __init__(self, verbose=True):
        self.verbose = verbose

    def startTest(self, test):
        self.snapshot = self.makeSnapshot()

    def stopTest(self, test):
        new_snapshot = self.makeSnapshot()
        if new_snapshot != self.snapshot:
            warn("%s changed logging configuration" % name_of_test(test))
            if self.verbose:
                old_loggers = sets.Set(self.snapshot.keys())
                new_loggers = sets.Set(new_snapshot.keys())
                for name in sorted(old_loggers | new_loggers):
                    if name not in new_loggers:
                        warn("  logger %s disappeared" % name)
                    elif name not in old_loggers:
                        warn("  new logger: %s" % name)
                    else:
                        old = self.snapshot[name]
                        new = new_snapshot[name]
                        if old != new:
                            warn("  logger %s was changed" % name)

    def makeSnapshot(self):
        import logging
        info = {}
        for name, logger in logging.root.manager.loggerDict.items():
            if isinstance(logger, logging.PlaceHolder):
                continue
            if (logger.level == 0 and logger.propagate and not logger.disabled
                and not logger.handlers):
                continue
            info[name] = {'level': logger.level,
                          'disabled': logger.disabled,
                          'propagate': logger.propagate,
                          'handlers': list(logger.handlers)}
        return info


class CleanUpChecks:
    """Try to detect unit tests that perform placeless setup, but not teardown.

    The check actually counts the number of times CleanUp().cleanUp() is called
    during the setup, test itself, and teardown.  Since both placelessSetUp
    and placelessTearDown call CleanUp().cleanUp(), we expect to see at least
    two cleanups during that time.  If we see only one, something is wrong.
    """

    def __init__(self):
        from zope.testing.cleanup import addCleanUp
        self._testThatCalledCleanUp = {}
        self._current_test = None
        addCleanUp(self.doCleanUp)

    def doCleanUp(self):
        assert self._current_test is not None
        self._testThatCalledCleanUp.setdefault(self._current_test, 0)
        self._testThatCalledCleanUp[self._current_test] += 1

    def startTest(self, test):
        self._current_test = test

    def stopTest(self, test):
        count = self._testThatCalledCleanUp.get(test, 0)
        if count == 1:
            warn("%s called CleanUp only once"
                 " (probably in setUp, but not in tearDown)" % test.id())
        self._current_test = None


def test_hooks():
    return [
        StdoutChecks(),     # should be the first one
        TransactionChecks(),
        LibxmlChecks(),
        LoggingChecks(),
        CleanUpChecks(),
    ]
