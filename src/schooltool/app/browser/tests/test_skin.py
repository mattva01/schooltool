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
Tests for schooltool.app.browser.skin.

$Id: test_skin.py 2643 2005-02-01 11:13:58Z mg $
"""

import unittest
import pprint

from zope.interface import providedBy
from zope.testing import doctest
from zope.app.testing import setup, ztapi


def doctest_NavigationViewlet_cmp():
    r"""Tests for NavigationViewlet.__cmp__

        >>> from schooltool.app.browser.skin import NavigationViewlet

    If two viewlets have an ``order`` attribute, they are ordered by it.
    This attribute may be a string, if defined via zcml.

        >>> v1 = NavigationViewlet()
        >>> v2 = NavigationViewlet()
        >>> orders = [-5, 1, 5, 20, '-5', '1', '5', '20']
        >>> for v1.order in orders:
        ...     for v2.order in orders:
        ...         assert cmp(v1, v2) == cmp(int(v1.order), int(v2.order)), \
        ...                 (v1.order, v2.order, cmp(v1, v2))
        ...         assert cmp(v2, v1) == cmp(int(v2.order), int(v1.order)), \
        ...                 (v1.order, v2.order, cmp(v1, v2))

    If two viewlets do not have an ``order`` attribute, they are ordered
    alphabetically by their ``title`` attributes.

        >>> v1 = NavigationViewlet()
        >>> v2 = NavigationViewlet()
        >>> titles = ['Hello', 'World', 'Apple', 'Tangerine']
        >>> for v1.title in titles:
        ...     for v2.title in titles:
        ...         assert cmp(v1, v2) == cmp(v1.title, v2.title), \
        ...                 (v1.title, v2.title, cmp(v1, v2))
        ...         assert cmp(v2, v1) == cmp(v2.title, v1.title), \
        ...                 (v1.title, v2.title, cmp(v1, v2))

    If it so happens that one viewlet has an ``order`` attribute, and the other
    doesn't, the one with an order comes first.

        >>> v1 = NavigationViewlet()
        >>> v1.order = 42
        >>> v2 = NavigationViewlet()
        >>> v2.title = 'Um...'
        >>> cmp(v1, v2) < 0
        True
        >>> cmp(v2, v1) > 0
        True

    Here's an illustration:

        >>> def viewlet(title, order=None):
        ...     v = NavigationViewlet()
        ...     v.title = title
        ...     if order is not None:
        ...         v.order = order
        ...     return v
        >>> viewlets = [
        ...     viewlet('One', 1),
        ...     viewlet('Apple'),
        ...     viewlet('Twenty-two', 22),
        ...     viewlet('Five', 5),
        ...     viewlet('Orange'),
        ...     viewlet('Grapefuit')
        ... ]
        >>> viewlets.sort()
        >>> for v in viewlets:
        ...     print v.title
        One
        Five
        Twenty-two
        Apple
        Grapefuit
        Orange

    """


def doctest_schoolToolTraverseSubscriber():
    """Tests for schoolToolTraverseSubscriber.

    We subscribe to Zope's BeforeTraverseEvent and apply the SchoolTool skin
    whenever an ISchoolToolApplication is traversed during URL traversal.

        >>> from zope.publisher.browser import TestRequest
        >>> from zope.app.publication.zopepublication import BeforeTraverseEvent
        >>> from schooltool.app.browser.skin import schoolToolTraverseSubscriber
        >>> from schooltool.app.browser.skin import ISchoolToolSkin
        >>> from schooltool.app.app import SchoolToolApplication

        >>> ob = SchoolToolApplication()
        >>> request = TestRequest()
        >>> ev = BeforeTraverseEvent(ob, request)
        >>> schoolToolTraverseSubscriber(ev)
        >>> ISchoolToolSkin.providedBy(request)
        True
        >>> skin = list(providedBy(request).interfaces())[1]
        >>> skin
        <InterfaceClass schooltool.app.browser.skin.ISchoolToolSkin>
        >>> pprint.pprint(skin.getBases())
        (<InterfaceClass schooltool.app.browser.skin.ISchoolToolLayer>,
         <InterfaceClass zope.publisher.interfaces.browser.IDefaultBrowserLayer>)


    The skin is, obviously, not applied if you traverse some other object

        >>> ob = object()
        >>> request = TestRequest()
        >>> ev = BeforeTraverseEvent(ob, request)
        >>> schoolToolTraverseSubscriber(ev)
        >>> ISchoolToolSkin.providedBy(request)
        False

    """


def test_suite():
    return unittest.TestSuite([
                doctest.DocTestSuite(),
           ])


if __name__ == "__main__":
    unittest.main(defaultTest='test_suite')
