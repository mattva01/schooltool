#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003 Shuttleworth Foundation
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
SchoolTool functional tests from script files.

Script files should be named *.scr and placed in the same directory as this
module.

The first paragraph (everything up to and including the first blank line)
of a script file is ignored.  Use it for descriptions.

Lines starting with 'SchoolTool> ' are input; they are piped to the command
line client (with the prefix stripped).  Other lines are output, they are
compared with what the command line client outputs.
"""

import unittest
import os
import re
import sys
from threading import Thread
from schooltool.tests.helpers import unidiff, normalize_xml

__metaclass__ = type

try:
    from popen2 import Popen4
except ImportError:
    # Win32 does not have Popen4
    from popen2 import popen4

    class Popen4:

        def __init__(self, cmd):
            self.fromchild, self.tochild = popen4(cmd)

        def wait(self):
            # Is there a way to get the real status code on Win32?
            return 0


class Reader(Thread):
    """A thread for reading from a pipe in the background."""

    def __init__(self, pipe):
        Thread.__init__(self)
        self.pipe = pipe

    def run(self):
        self.result = self.pipe.read()
        self.pipe.close()


class ScriptTestCase(unittest.TestCase):

    prefix = re.compile('^SchoolTool> |^PUT> |^POST> ')
    client_args = '-p 8813'
    child_startup = 'user manager schooltool\n'
    child_startup_expected = ['User manager\n', '\n']

    def __init__(self, script):
        unittest.TestCase.__init__(self)
        self.script = script
        dirname = os.path.dirname(__file__)
        self.filename = os.path.join(dirname, script)
        self.client = os.path.abspath(
                os.path.join(dirname, '..', 'clients', 'client.py'))

    def __str__(self):
        return 'script %s' % self.script

    def id(self):
        return 'script %s' % self.script

    def runTest(self):
        cmd = "%s %s %s" % (sys.executable, self.client, self.client_args)
        child = Popen4(cmd)
        reader = Reader(child.fromchild)
        reader.start()
        child.tochild.write(self.child_startup)
        expected = list(self.child_startup_expected)
        orig_lineno = [0] * len(expected)
        f = open(self.filename)
        skipping_intro = True
        magic = False
        in_ical = False
        for lineno, line in enumerate(f):
            if skipping_intro:
                if not line.strip():
                    skipping_intro = False
                continue
            m = self.prefix.match(line)
            if m is not None:
                child.tochild.write(line[m.end():])
            else:
                if line.startswith('##'): # comments
                    continue
                if '*' in line or line.startswith('%% XML'):
                    magic = True
                elif line.startswith('BEGIN:VCALENDAR'):
                    in_ical = True
                elif line.startswith('END:VCALENDAR'):
                    in_ical = False
                if in_ical and '\r' not in line:
                    line = line.replace('\n', '\r\n')
                expected.append(line)
                orig_lineno.append(lineno + 1)
        child.tochild.close()
        f.close()
        reader.join()
        result = reader.result
        exitcode = child.wait()
        self.assertEqual(exitcode, 0, "child returned exit code %d" % exitcode)
        if magic:
            # cannot use SequenceMatcher here
            result = result.splitlines(True)
            eidx = ridx = 0
            while eidx < len(expected) and ridx < len(result):
                e = expected[eidx]
                r = result[ridx]
                if e.startswith('%% XML'):
                    recursively_sort = []
                    prefix = '%% XML recursively_sort='
                    if e.startswith(prefix):
                        recursively_sort = e[len(prefix):].split()
                    eidx += 1
                    orig_start = orig_lineno[eidx]
                    start_idx = eidx
                    while (eidx < len(expected) and
                           not expected[eidx].startswith('%% END XML')):
                        eidx += 1
                    expected_xml = ''.join(expected[start_idx:eidx])
                    expected_xml = normalize_xml(expected_xml,
                                      recursively_sort=recursively_sort)
                    eidx += 1

                    if eidx < len(expected):
                        e = expected[eidx]
                    else:
                        e = None
                    start_idx = ridx
                    while ridx < len(result) and result[ridx] != e:
                        ridx += 1
                    result_xml = ''.join(result[start_idx:ridx])
                    result_xml = normalize_xml(result_xml,
                                      recursively_sort=recursively_sort)
                    self.assertEqual(expected_xml, result_xml,
                                     "%s, near line %d\n%s"
                                     % (self.script, orig_start,
                                        unidiff(expected_xml, result_xml)))
                elif '*' in e:
                    rx = re.escape(e).replace(r'\*', '.*') + '$'
                    if re.match(rx, r) is None:
                        break
                    eidx += 1
                    ridx += 1
                elif e == r:
                    eidx += 1
                    ridx += 1
                else:
                    break
            if eidx < len(expected) or ridx < len(result):
                # difference found
                context_start = max(0, eidx-5)
                orig_start = orig_lineno[context_start]
                diffs = ["@@ -%d..%d @@\n"
                         % (orig_start,
                            orig_lineno[min(eidx, len(expected)-1)])]
                context = expected[context_start:eidx]
                diffs += [" " + s for s in context]
                diffs += ["-" + s for s in expected[eidx:eidx+3]]
                diffs += ["+" + s for s in result[ridx:ridx+3]]
                self.fail("Output does not match expectations\n%s..."
                          % "".join(diffs))
        else:
            expected = "".join(expected)
            self.assertEqual(expected, result, "%s\n%s" % (self.script,
                                                    unidiff(expected, result)))


class AppLogSetup(unittest.TestCase):
    """This just clears the app log and fills it up with some data.

    This should be moved to a global test setup, once there is such a
    thing.

    XXX: This might not work on Windows, because the log file may already
         be opened by another process.
    """

    def test(self):
        # The same file name should be specified in test.conf
        log = file("testserver_app.log", "w")
        for l in range(1, 21):
            print >> log, "Ftest log line %d" % l
        log.close()


def find_scripts():
    dirname = os.path.dirname(__file__)
    files = [fn for fn in os.listdir(dirname) if fn.endswith('.scr')]
    files.sort()
    return files


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(AppLogSetup))
    for script in find_scripts():
        suite.addTest(ScriptTestCase(script))
    return suite

if __name__ == '__main__':
    unittest.main()
