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
from zope.interface import implements
from zope.testing import doctest
from zope.publisher.browser import TestRequest


def doctest_NavigationView():
    """Unit tests for NavigationView.

    This view works for any ILocatable object within a SchoolTool instance.

      >>> from schooltool.app import SchoolToolApplication, Person
      >>> from zope.app.component.hooks import setSite
      >>> from zope.app.component.site import LocalSiteManager
      >>> app = SchoolToolApplication()
      >>> app.setSiteManager(LocalSiteManager(app))
      >>> setSite(app)
      >>> p = Person('1')
      >>> app['persons']['1'] = p

    It makes the application available as `view.app`:

      >>> from schooltool.browser import NavigationView
      >>> view = NavigationView(p, None)
      >>> view.app is app
      True

    """


def doctest_TimetabledTraverser():
    """Tests for TimetabledTraverser.

        >>> from schooltool.browser import TimetabledTraverser
        >>> class TimetabledStub:
        ...     timetables = 'Timetables'
        ...     calendar = 'Calendar'
        >>> request = TestRequest()
        >>> t = TimetabledTraverser(TimetabledStub(), request)

    If we ask for timetables, the corresponding object will be returned:

        >>> t.publishTraverse(request, 'timetables')
        'Timetables'

    By the way, this traverser inherits from CalendarOwnerTraverser:

        >>> t.publishTraverse(None, 'calendar')
        'Calendar'

        >>> t.publishTraverse(None, 'foobar') # doctest: +ELLIPSIS
        Traceback (most recent call last):
          ...
        NotFound: Object: <...TimetabledStub instance at 0x...>, name: 'foobar'

    """


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite())
    suite.addTest(doctest.DocTestSuite('schoolbell.app.browser'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
