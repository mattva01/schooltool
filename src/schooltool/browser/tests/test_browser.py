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

$Id: test_browser.py 3710 2005-05-15 10:27:21Z gintas $
"""

import unittest
from zope.testing import doctest

from schoolbell.app.browser.tests.setup import setUp, tearDown
from schoolbell.app.testing import setup


def doctest_NavigationView():
    """Unit tests for NavigationView.

    This view works for any ILocatable object within a SchoolTool instance.

      >>> from schooltool.app import SchoolToolApplication
      >>> from schoolbell.app.person.person import Person
      >>> app = setup.setupSchoolBellSite()
      >>> p = Person('1')
      >>> app['persons']['1'] = p

    It makes the application available as `view.app`:

      >>> from schooltool.browser import NavigationView
      >>> view = NavigationView(p, None)
      >>> view.app is app
      True

    """


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(setUp=setUp, tearDown=tearDown))
    suite.addTest(doctest.DocTestSuite('schoolbell.app.browser'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
