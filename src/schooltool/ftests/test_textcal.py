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
A functional test for the textcal.py script.  An expected output is
stored in the file textcal-output.txt in this directory.

$Id$
"""

import unittest
import os
import re
from threading import Thread
from schooltool.tests.helpers import unidiff, normalize_xml

__metaclass__ = type


class TestTextCal(unittest.TestCase):

    def setUp(self):
        self._oldpythonpath = os.getenv("PYTHONPATH")

    def tearDown(self):
        if self._oldpythonpath:
            os.putenv("PYTHONPATH", self._oldpythonpath)

    def test(self):

        dirname = os.path.dirname(__file__)
        script = os.path.join(dirname, '..', 'textcal.py')
        config = os.path.join(dirname, '..', 'schema', 'tt-us-4day.xml')

        expected = file(os.path.join(dirname, 'textcal-output.txt')).read()

        pythonpath = os.path.join(dirname, '..', '..')
        os.putenv("PYTHONPATH", pythonpath)
        out = os.popen("python %s %s" % (script, config), "r")

        result = out.read()
        out.close()

        self.assertEqual(result, expected, unidiff(result, expected))


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestTextCal))
    return suite

if __name__ == '__main__':
    unittest.main()
