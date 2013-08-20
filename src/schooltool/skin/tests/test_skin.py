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
Tests for schooltool.app.browser.skin.
"""

import unittest
import doctest

from zope.interface import Interface, implements
from zope.app.testing import setup
from zope.publisher.browser import TestRequest
from zope.component import provideAdapter, adapts

from schooltool.testing.setup import setUpSchoolToolSite


def doctest_OrderedViewletManager_sort():
    r"""Tests for OrderedViewletManager.sort

        >>> from schooltool.skin import OrderedViewletManager

    If two viewlets have an ``order`` attribute, they are ordered by it.
    This attribute may be a string, if defined via zcml.

    If two viewlets do not have an ``order`` attribute, they are ordered
    alphabetically by their ``title`` attributes.

    If it so happens that one viewlet has an ``order`` attribute, and the other
    doesn't, the one with an order comes first.

        >>> class SomeViewlet(object):
        ...     def __init__(self, title=None, order=None):
        ...         if title is not None:
        ...             self.title = title
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

    Viewlets may not necessarily have a title, if they have an order.

        >>> viewlets = [
        ...     ('name1', SomeViewlet(order='1')),
        ...     ('name22', SomeViewlet(order='22')),
        ...     ('name5', SomeViewlet(order='5')),
        ... ]
        >>> for name, v in mgr.sort(viewlets):
        ...     print name
        name1
        name5
        name22

    Viewlets must have either an order or a title, and the error message
    should explicitly say which viewlet is at fault:

        >>> viewlets = [
        ...     ('name1', SomeViewlet(order='1')),
        ...     ('name2', SomeViewlet()),
        ...     ('name3', SomeViewlet(title='hi')),
        ... ]
        >>> mgr.sort(viewlets)
        Traceback (most recent call last):
          ...
        AttributeError: 'name2' viewlet has neither order nor title

    """


def doctest_NavigationViewlet_appURL():
    r"""Tests for NavigationViewlet.appURL

        >>> setup.placefulSetUp()
        >>> site = setUpSchoolToolSite()

        >>> from schooltool.skin import NavigationViewlet
        >>> viewlet = NavigationViewlet()
        >>> viewlet.request = TestRequest()
        >>> viewlet.appURL()
        'http://127.0.0.1'

        >>> setup.placefulTearDown()

    """


def doctest_NavigationViewletViewCrowd():
    """Tests for NavigationViewletViewCrowd.

        >>> setup.placelessSetUp()
        >>> from schooltool.skin.skin import NavigationViewletViewCrowd

        >>> class StubCrowd(object):
        ...     def __init__(self, context):
        ...         self.context = context
        ...     def contains(self, principal):
        ...         return "Crowd on %s contains %s" % (self.context, principal)

        >>> from schooltool.securitypolicy.interfaces import ICrowd
        >>> provideAdapter(StubCrowd,
        ...                (Interface, ), ICrowd, name='schooltool.view')

        >>> class ViewletStub(object):
        ...     def actualContext(self):
        ...         return "Actual context object"

    The crowd delegates the permission check to the ICrowd based on
    the actualContext object of the viewlet:

        >>> crowd = NavigationViewletViewCrowd(ViewletStub())
        >>> crowd.contains("The principal")
        'Crowd on Actual context object contains The principal'

        >>> setup.placelessTearDown()

    """


def doctest_ActionMenuViewletManager():
    """Tests for ActionMenuViewletManager.

         >>> setup.placelessSetUp()
         >>> from schooltool.skin.skin import ActionMenuViewletManager
         >>> context = "context"
         >>> request = TestRequest()
         >>> manager = ActionMenuViewletManager(context, request, None)

    Viewlet managers title is taken from it's contexts breadcrumb info:

         >>> manager.title()
         ''

    subItems is a shortctut that gets subitems for the managers context:

         >>> manager.getSubItems = lambda context: ["Sub menu items for", context]
         >>> manager.subItems()
         ['Sub menu items for', 'context']

         >>> setup.placelessTearDown()

    """


def doctest_ActionMenuViewletManager_update():
    """Tests for ActionMenuViewletManager.update.

         >>> setup.placelessSetUp()
         >>> from schooltool.skin.skin import ActionMenuViewletManager
         >>> context = "context"
         >>> request = TestRequest()
         >>> manager = ActionMenuViewletManager(context, request, None)

    Viewlet managers title is taken from it's contexts breadcrumb info:

         >>> class TargetStub(object):
         ...      __parent__ = "parent"
         >>> target = TargetStub()
         >>> manager.getSubItems = lambda context: ["foo", "bar"]
         >>> import sys
         >>> manager.orderedViewletManagerUpdate = lambda: sys.stdout.write(
         ...                                           "OrderedViewletManager.update()")
         >>> manager.__parent__ = ActionMenuViewletManager(None, None, None)
         >>> manager.target = target

    If we are not displaying a top level menu and the current target
    is not in the list of it's parents subitems:

         >>> manager.update()
         OrderedViewletManager.update()

    Target becomes the context:

         >>> target is manager.context
         True

    If we are displaying a top level menu we should still have the
    target becoming new context:

         >>> manager.context = None
         >>> manager.update()
         OrderedViewletManager.update()

         >>> target is manager.context
         True

    But if the manager is being displayed to display a top level menu,
    and the item is in it's parents subitem list:

         >>> manager.getSubItems = lambda context: ["foo", "bar", target]
         >>> manager.__parent__ = None

         >>> manager.update()
         OrderedViewletManager.update()

    We should get menu items of the targets parent:

         >>> target.__parent__ is manager.context
         True

         >>> setup.placelessTearDown()

    """


def doctest_LanguageSelectorViewlet():
    """

         >>> from schooltool.skin.skin import LanguageSelectorViewlet
         >>> from zope.publisher.browser import TestRequest
         >>> viewlet = LanguageSelectorViewlet(None, TestRequest())

         >>> from zope.i18n.interfaces import IUserPreferredLanguages
         >>> class UPL(object):
         ...     implements(IUserPreferredLanguages)
         ...     adapts(Interface)
         ...     def __init__(self, request):
         ...         pass

     If ICookieLanguageSelector is not provided by the
     UserPreferedLanguages adapter - no languages are in the list:

         >>> provideAdapter(UPL)
         >>> viewlet.languages() is None
         True

     If adapter provides ICookieLanguageSelector viewlet returns
     whatever is given by the CookieLanguageSelector:

         >>> from zope.publisher.interfaces.http import IHTTPRequest
         >>> from schooltool.app.interfaces import ICookieLanguageSelector
         >>> class CookieLanguageSelector(UPL):
         ...     implements(ICookieLanguageSelector)
         ...     adapts(IHTTPRequest)
         ...     def getLanguageList(self):
         ...         return ["lt", "en"]
         ...     def getSelectedLanguage(self):
         ...         return "lt"
         >>> provideAdapter(CookieLanguageSelector, provides=IUserPreferredLanguages)

         >>> viewlet.languages()
         ['lt', 'en']

         >>> viewlet.selected_lang()
         'lt'

    """


def test_suite():
    return unittest.TestSuite([
                doctest.DocTestSuite(),
           ])


if __name__ == "__main__":
    unittest.main(defaultTest='test_suite')
