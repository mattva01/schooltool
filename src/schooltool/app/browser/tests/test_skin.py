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


def doctest_viewletClasses():
    """Test the viewlet classes.

    In the skin module we define a couple of helper functions to make it
    simpler to create viewlets for common patterns, such as the insertion of
    CSS or JS links in the template.

    First, we have to make create  placeful setup and register a resource:

      >>> setup.placefulSetUp()
      >>> setup.setUpTraversal()

      >>> from zope.app.traversing.interfaces import ITraversable
      >>> from zope.app.traversing.namespace import resource
      >>> ztapi.provideAdapter(None, ITraversable, resource, name="resource")
      >>> ztapi.provideView(None, None, ITraversable, "resource", resource)

      >>> from zope.app.publisher.browser.resource import Resource
      >>> class Style(Resource):
      ...     __name__ = 'style.css'

      >>> ztapi.browserResource('style.css', Style)

    Now we can create the viewlet for the resource:

      >>> from schooltool.app.browser import skin
      >>> CSSViewletClass = skin.CSSViewlet('style.css')

    During the render process the following happens:

      >>> from zope.publisher.browser import TestRequest
      >>> css_viewlet = CSSViewletClass(object(), TestRequest(), None)
      >>> print css_viewlet().strip()
      <link type="text/css" rel="stylesheet"
            href="http://127.0.0.1/@@/style.css" />

    Let's repeat this demonstration for the Javascript version:

      >>> class Menu(Resource):
      ...     __name__ = 'menu.js'
      >>> ztapi.browserResource('menu.js', Menu)

      >>> JSViewletClass = skin.JavaScriptViewlet('menu.js')
      >>> js_viewlet = JSViewletClass(object(), TestRequest(), None)
      >>> print js_viewlet().strip()
      <script type="text/javascript"
              src="http://127.0.0.1/@@/menu.js">
      </script>

      >>> setup.placefulTearDown()

    """


def test_suite():
    return unittest.TestSuite([
                doctest.DocTestSuite(),
           ])


if __name__ == "__main__":
    unittest.main(defaultTest='test_suite')
