#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2005 Shuttleworth Foundation
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
Tests for schoolbell views.

$Id$
"""
import unittest
from zope.testing import doctest

from schooltool.app.browser.testing import setUp, tearDown
from schooltool.testing import setup

def doctest_NavigationView():
    """Unit tests for NavigationView.

    This view works for any ILocatable object within a SchoolBell instance.

      >>> app = setup.setupSchoolToolSite()

      >>> from schooltool.person.person import Person
      >>> p = Person('1')
      >>> app['persons']['1'] = p

    It makes the application available as `view.app`:

      >>> from schooltool.app.browser import NavigationView
      >>> view = NavigationView(p, None)
      >>> view.app is app
      True

    """

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                       optionflags=doctest.ELLIPSIS))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
