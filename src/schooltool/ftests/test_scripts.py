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
from popen2 import Popen4
from threading import Thread
from schooltool.tests.helpers import unidiff

__metaclass__ = type


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

    def __init__(self, script):
        unittest.TestCase.__init__(self)
        self.script = script
        dirname = os.path.dirname(__file__)
        self.filename = os.path.join(dirname, script)
        self.client = os.path.abspath(os.path.join(dirname, '..', 'client.py'))

    def __str__(self):
        return 'script %s' % self.script

    def id(self):
        return 'script %s' % self.script

    def runTest(self):
        cmd = "python2.3 %s" % self.client
        child = Popen4(cmd)
        reader = Reader(child.fromchild)
        reader.start()
        expected = []
        orig_lineno = []
        f = open(self.filename)
        skipping_intro = True
        magic = False
        for lineno, line in enumerate(f):
            if skipping_intro:
                if not line.strip():
                    skipping_intro = False
                continue
            m = self.prefix.match(line)
            if m is not None:
                child.tochild.write(line[m.end():])
            else:
                if '*' in line:
                    magic = True
                expected.append(line)
                orig_lineno.append(lineno + 1)
        child.tochild.close()
        f.close()
        reader.join()
        result = reader.result
        exitcode = child.wait()
        self.assertEqual(exitcode, 0, "child returned exit code %d" % exitcode)
        if magic:
            # cannot use SequenceMatcher here, wildcards do not hash the same
            # as the lines they match
            result = result.splitlines(True)
            for idx, (e, r) in enumerate(zip(expected, result)):
                if e == r:
                    continue
                if '*' in e:
                    rx = re.escape(e).replace(r'\*', '.*') + '$'
                    if re.match(rx, r) is not None:
                        continue
                context_start = max(0, idx-5)
                orig_start = orig_lineno[context_start]
                diffs = ["@@ -%d..%d @@\n"
                         % (orig_start, orig_lineno[idx])]
                context = result[context_start:idx]
                diffs += [" " + s for s in context] + ["-" + e, "+" + r]
                self.fail("Output does not match expectations\n%s..."
                          % "".join(diffs))
        else:
            expected = "".join(expected)
            self.assertEqual(expected, result, "%s\n%s" % (self.script,
                                                    unidiff(expected, result)))


def find_scripts():
    dirname = os.path.dirname(__file__)
    files = [fn for fn in os.listdir(dirname) if fn.endswith('.scr')]
    files.sort()
    return files


def test_suite():
    suite = unittest.TestSuite()
    for script in find_scripts():
        suite.addTest(ScriptTestCase(script))
    return suite

if __name__ == '__main__':
    unittest.main()
