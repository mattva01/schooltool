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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Tests for schooltool error views.
"""

import unittest
import doctest

from zope.publisher.browser import TestRequest
from zope.browser.interfaces import ISystemErrorView


def doctest_ErrorView():
    r"""Test for ErrorView

        >>> from schooltool.skin.error import ErrorView
        >>> exception = RuntimeError("some kind of error")
        >>> request = TestRequest()
        >>> view = ErrorView(exception, request)

    The view is a system error view, thus causing the zope publication to
    log exceptions via the SiteError logger.

        >>> ISystemErrorView.providedBy(view)
        True
        >>> view.isSystemError()
        True

    view.index is a page template, normally specified via ZCML

        >>> view.index = lambda: 'rendered page'

    Rendering the view sets the status code to 500.

        >>> print view()
        rendered page

        >>> request.response.getStatus()
        500

    view.traceback uses sys.exc_info, and apparently we have to test it inside
    an except clause

        >>> try:
        ...     raise exception
        ... except:
        ...     print view.traceback
        File "<span class="filename">&lt;doctest...doctest_ErrorView[...]&gt;</span>",
          line <span class="lineno">2</span>, in <span class="method">...</span>
          <span class="source">raise exception</span>

    """


def test_suite():
    optionflags = (doctest.ELLIPSIS | doctest.REPORT_NDIFF |
                   doctest.NORMALIZE_WHITESPACE |
                   doctest.REPORT_ONLY_FIRST_FAILURE)
    return doctest.DocTestSuite(optionflags=optionflags)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
