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
Unit tests for graphclient.py
"""

import unittest

__metaclass__ = type


class TestGraphClient(unittest.TestCase):

    def test(self):
        import schooltool.clients.graphclient # at least check that it imports
        self.assert_(schooltool.clients.graphclient)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestGraphClient))
    return suite

if __name__ == '__main__':
    unittest.main()
