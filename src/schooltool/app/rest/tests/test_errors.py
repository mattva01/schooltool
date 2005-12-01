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
Tests for schooltool.rest.app.errors.

$Id$
"""

import unittest

from zope.testing import doctest
from zope.publisher.browser import TestRequest
from zope.app.exception.interfaces import ISystemErrorView


def doctest_TextErrorView():
    """Tests for TextErrorView.

        >>> from schooltool.app.rest.errors import TextErrorView
        >>> exc = Exception("something went wrong")
        >>> view = TextErrorView(exc, TestRequest())

        >>> print view()
        something went wrong

        >>> view.request.response.getStatus()
        400
        >>> view.request.response.getHeader('Content-Type')
        'text/plain; charset=utf-8'

    """


def doctest_XMLErrorView():
    """Tests for XMLErrorView.

        >>> from schooltool.app.rest.errors import XMLErrorView
        >>> exc = Exception("something went wrong while parsing XML")
        >>> view = XMLErrorView(exc, TestRequest())

        >>> print view()
        something went wrong while parsing XML

        >>> view.request.response.getStatus()
        400
        >>> view.request.response.getHeader('Content-Type')
        'text/plain; charset=utf-8'

    """


def doctest_ICalParseErrorView():
    """Tests for ICalParseErrorView.

        >>> from schooltool.app.rest.errors import ICalParseErrorView
        >>> exc = Exception("more info")
        >>> view = ICalParseErrorView(exc, TestRequest())

        >>> print view()
        Error parsing iCalendar data: more info

        >>> view.request.response.getStatus()
        400
        >>> view.request.response.getHeader('Content-Type')
        'text/plain; charset=utf-8'

    """


def doctest_DependencyErrorView():
    """Tests for DependencyErrorView.

        >>> from schooltool.app.rest.errors import DependencyErrorView
        >>> exc = Exception("something couldn't be deleted")
        >>> view = DependencyErrorView(exc, TestRequest())

        >>> print view()
        Cannot delete system objects.

        >>> view.request.response.getStatus()
        405
        >>> view.request.response.getHeader('Content-Type')
        'text/plain; charset=utf-8'

    """


def doctest_SystemErrorView():
    """Tests for SystemErrorView.

        >>> from schooltool.app.rest.errors import SystemErrorView
        >>> exc = Exception("something broke")
        >>> view = SystemErrorView(exc, TestRequest())

        >>> print view()
        A system error has occurred.

        >>> view.request.response.getStatus()
        500
        >>> view.request.response.getHeader('Content-Type')
        'text/plain; charset=utf-8'

    The view is a system error view, thus causing the zope publication to
    log exceptions via the SiteError logger.

        >>> ISystemErrorView.providedBy(view)
        True
        >>> view.isSystemError()
        True

    """


def test_suite():
    return doctest.DocTestSuite()


if __name__=='__main__':
    unittest.main(defaultTest='test_suite')
