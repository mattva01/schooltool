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
Unit tests for schooltool.unchanged

$Id$
"""

import unittest

__metaclass__ = type


class TestUnchanged(unittest.TestCase):

    def test(self):
        from StringIO import StringIO
        from cPickle import Pickler, Unpickler
        from schooltool.unchanged import UnchangedClass, Unchanged
        unchanged1 = UnchangedClass()
        self.assert_(unchanged1 is Unchanged)
        self.assert_(Unchanged is not UnchangedClass)

        self.assertRaises(TypeError, lambda: Unchanged < Unchanged)
        self.assertRaises(TypeError, lambda: Unchanged <= Unchanged)
        self.assertRaises(TypeError, lambda: Unchanged > Unchanged)
        self.assertRaises(TypeError, lambda: Unchanged >= Unchanged)
        self.assert_(Unchanged == Unchanged)
        self.assert_(not (Unchanged != Unchanged))
        self.assert_(Unchanged != object())
        self.assert_(not (Unchanged == object()))

        s = StringIO()
        p = Pickler(s)
        p.dump(unchanged1)
        s.seek(0)
        u = Unpickler(s)
        unchanged2 = u.load()

        self.assert_(unchanged2 is Unchanged)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestUnchanged))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
