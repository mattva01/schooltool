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
from zope.publisher.browser import TestRequest
from zope.app.publication.zopepublication import BeforeTraverseEvent

from schooltool.testing.setup import setupSchoolToolSite


def doctest_OrderedViewletManager_sort():
    r"""Tests for OrderedViewletManager.sort

        >>> from schooltool.app.browser.skin import OrderedViewletManager

    If two viewlets have an ``order`` attribute, they are ordered by it.
    This attribute may be a string, if defined via zcml.

    If two viewlets do not have an ``order`` attribute, they are ordered
    alphabetically by their ``title`` attributes.

    If it so happens that one viewlet has an ``order`` attribute, and the other
    doesn't, the one with an order comes first.

        >>> class SomeViewlet(object):
        ...     def __init__(self, title, order=None):
        ...         self.title = title
        ...         if order is not None:
        ...             self.order = order

        >>> mgr = OrderedViewletManager(context=None, request=None, view=None)
        >>> viewlets = [
        ...     ('name1', SomeViewlet('One', '1')),
        ...     ('name2', SomeViewlet('Apple')),
        ...     ('name3', SomeViewlet('Twenty-two', '22')),
        ...     ('name4', SomeViewlet('Five', '5')),
        ...     ('name5', SomeViewlet('Orange')),
        ...     ('name6', SomeViewlet('Grapefuit')),
        ... ]
        >>> for name, v in mgr.sort(viewlets):
        ...     print v.title
        One
        Five
        Twenty-two
        Apple
        Grapefuit
        Orange

    """


def doctest_NavigationViewlet_appURL():
    r"""Tests for NavigationViewlet.appURL

        >>> setup.placefulSetUp()
        >>> site = setupSchoolToolSite()

        >>> from schooltool.app.browser.skin import NavigationViewlet
        >>> viewlet = NavigationViewlet()
        >>> viewlet.request = TestRequest()
        >>> viewlet.appURL()
        'http://127.0.0.1'

        >>> setup.placefulTearDown()

    """


def doctest_schoolToolTraverseSubscriber():
    """Tests for schoolToolTraverseSubscriber.

    We subscribe to Zope's BeforeTraverseEvent and apply the SchoolTool skin
    whenever an ISchoolToolApplication is traversed during URL traversal.

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
