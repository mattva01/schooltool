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
Setup code for SchoolTool application browser unit tests
"""
import os.path
import unittest

import transaction
from zope.interface import implements, Interface
from zope.component import provideAdapter, provideUtility
from zope.component.hooks import setSite
from zope.app.testing.functional import FunctionalTestSetup
from zope.app.testing import setup, ztapi
from zope.app.form.interfaces import IInputWidget
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.publisher.interfaces.browser import IDefaultBrowserLayer
from zope.schema.interfaces import \
        IPassword, ITextLine, IText, IBytes, IBool, ISet, IList, IDate, \
        IInt, IChoice, IIterableVocabulary, IVocabularyTokenized, \
        ICollection
from zope.app.form.browser import \
        PasswordWidget, TextWidget, BytesWidget, CheckBoxWidget, \
        DateWidget, IntWidget, ChoiceInputWidget, DropdownWidget, \
        TextAreaWidget, ChoiceCollectionInputWidget, \
        CollectionInputWidget, MultiSelectWidget, OrderedMultiSelectWidget
from zope.app.form.interfaces import IWidgetInputError
from zope.app.form.browser.interfaces import IWidgetInputErrorView
from zope.app.form.browser.exception import WidgetInputErrorView
from zope.traversing.interfaces import ITraversable
from zope.traversing.namespace import view, resource
from zope.traversing.interfaces import IPathAdapter
from zope.browserpage.simpleviewclass import SimpleViewClass
from zope.app.basicskin.standardmacros import StandardMacros
from zope.app.form.browser.macros import FormMacros
from zope.browsermenu.menu import MenuAccessView
from zope.browsermenu.interfaces import IBrowserMenu
from zope.publisher.interfaces.browser import IBrowserView

from schooltool.relationship.tests import setUpRelationships
from schooltool.skin.macros import SchoolToolMacros

from schooltool.app.browser import SchoolToolAPI, SortBy

class BrowserMenuStub(object):
    """A stub that fakes browser menu.

    So we could display schooltool_actions menu in unit tests.
    """

    implements(IBrowserMenu)

    id = None
    title = None
    description = None

    def __init__(self, id, title=u'', description=u''):
        self.id = id
        self.title = title
        self.description = description

    def getMenuItems(self, object, request):
        return []


def setUp(test=None):
    """Set up the test fixture for schooltool.app.browser doctests.

    Performs what is called a "placeless setup" in the Zope 3 world, then sets
    up annotations, relationships, and registers widgets as views for some
    schema fields.

    In effect, duplicates a subset of ZCML configuration -- just enough to
    actually render our page templates in unit tests.
    """
    setup.placefulSetUp()
    setup.setUpAnnotations()
    setup.setUpTraversal()
    # relationships
    setUpRelationships()
    # widgets
    ztapi.browserViewProviding(IPassword, PasswordWidget, IInputWidget)
    ztapi.browserViewProviding(ITextLine, TextWidget, IInputWidget)
    ztapi.browserViewProviding(IText, TextAreaWidget, IInputWidget)
    ztapi.browserViewProviding(IBytes, BytesWidget, IInputWidget)
    ztapi.browserViewProviding(IBool, CheckBoxWidget, IInputWidget)
    ztapi.browserViewProviding(IDate, DateWidget, IInputWidget)
    ztapi.browserViewProviding(IInt, IntWidget, IInputWidget)
    ztapi.browserViewProviding(IChoice, ChoiceInputWidget, IInputWidget)
    ztapi.browserViewProviding(ICollection, CollectionInputWidget, IInputWidget)

    ztapi.provideMultiView((IChoice, IIterableVocabulary), IBrowserRequest,
                           IInputWidget, '', DropdownWidget)

    ztapi.provideMultiView((ISet, IChoice), IBrowserRequest,
                           IInputWidget, '', ChoiceCollectionInputWidget)
    ztapi.provideMultiView((IList, IChoice), IBrowserRequest,
                           IInputWidget, '', ChoiceCollectionInputWidget)
    ztapi.provideMultiView((IList, IVocabularyTokenized), IBrowserRequest,
                           IInputWidget, '', OrderedMultiSelectWidget)
    # XXX MultiSelectWidget doesn't work with sets :/
    #     http://www.zope.org/Collectors/Zope3-dev/360
    ztapi.provideMultiView((ISet, IIterableVocabulary), IBrowserRequest,
                           IInputWidget, '', MultiSelectWidget)

    # errors in forms
    ztapi.browserViewProviding(IWidgetInputError, WidgetInputErrorView,
                               IWidgetInputErrorView)


    # Now, the question is: does the speed of the tests run with the
    # setup below justify this complex setup that duplicates the ZCML?
    # For now, I say yes. -- not mg, perhaps alga or gintas

    # ++view++
    ztapi.provideView(None, None, ITraversable, 'view', view)
    ztapi.provideView(None, None, ITraversable, 'resource', resource)

    # schooltool: namespace in tal
    provideAdapter(SchoolToolAPI, (None,), IPathAdapter, 'schooltool')

    # sortby: namespace in tal
    provideAdapter(SortBy, (None,), IPathAdapter, 'sortby')

    # standard_macros, schooltool_macros and schooltool_navigation
    ztapi.browserView(None, 'standard_macros', StandardMacros)
    ztapi.browserView(None, 'view_macros',
                      SimpleViewClass("../../skin/templates/view_macros.pt"))

    ztapi.browserView(None, 'schooltool_macros', SchoolToolMacros)
    ztapi.browserView(None, 'calendar_macros',
                      SimpleViewClass("./templates/calendar_macros.pt"))
    ztapi.browserView(None, 'generic_macros',
                      SimpleViewClass("../../skin/templates/generic_macros.pt"))

    # form macros
    ztapi.browserView(None, 'form_macros', FormMacros)
    import zope.formlib
    base = zope.formlib.__path__[0]
    ztapi.browserView(None, 'widget_macros',
                      SimpleViewClass(os.path.join(base, 'widget_macros.pt')))

    # resources
    class ResourceStub:
        def __init__(self, request):
            self.request = request
        def __getitem__(self, key):
            return ResourceStub(self.request)
        def __call__(self):
            return "a dummy resource"

    for name in ['layout.css', 'schooltool.css', 'schooltool.js',
                 'next.png', 'prev.png', 'favicon.ico',
                 'print.css', 'jquery.js',
                 'zonki-regular.png']:
        ztapi.browserResource(name, ResourceStub)

    # menus
    ztapi.browserView(None, 'view_get_menu', MenuAccessView)
    provideUtility(BrowserMenuStub('schooltool_actions'), IBrowserMenu,
                   'schooltool_actions')

    # `provider` TALES namespaces
    from zope.browserpage import metaconfigure
    from zope.contentprovider import tales
    metaconfigure.registerType('provider', tales.TALESProviderExpression)

    # viewlet manager registrations
    from zope.viewlet import manager
    from schooltool import skin
    name = 'schooltool.Header'
    provideAdapter(
        manager.ViewletManager(name, skin.IHeaderManager),
        (Interface, IDefaultBrowserLayer, IBrowserView),
        skin.IHeaderManager,
        name=name)

    name = 'schooltool.JavaScript'
    provideAdapter(
        manager.ViewletManager(name, skin.IJavaScriptManager),
        (Interface, IDefaultBrowserLayer, IBrowserView),
        skin.IJavaScriptManager,
        name=name)

    name = 'schooltool.CSS'
    provideAdapter(
        manager.ViewletManager(name, skin.ICSSManager),
        (Interface, IDefaultBrowserLayer, IBrowserView),
        skin.ICSSManager,
        name=name)

    name = 'schooltool.MenuBar'
    provideAdapter(
        manager.ViewletManager(name, skin.skin.IMenuBarMenuManager),
        (Interface, IDefaultBrowserLayer, IBrowserView),
        skin.skin.IMenuBarMenuManager,
        name=name)

    name = 'schooltool.NavigationMenu'
    provideAdapter(
        manager.ViewletManager(name, skin.skin.INavigationManager),
        (Interface, IDefaultBrowserLayer, IBrowserView),
        skin.skin.INavigationManager,
        name=name)

    name = 'schooltool.ActionsMenu'
    provideAdapter(
        manager.ViewletManager(name, skin.skin.IActionMenuManager),
        (Interface, IDefaultBrowserLayer, IBrowserView),
        skin.skin.IActionMenuManager,
        name=name)


def tearDown(test=None):
    """Tear down the test fixture for schooltool.app.browser doctests."""
    transaction.abort()
    setup.placefulTearDown()


def layeredTestSetup():
    fts = FunctionalTestSetup()
    fts.setUp()
    app = fts.getRootFolder()
    setSite(app)


def layeredTestTearDown():
    setSite(None)
    fts = FunctionalTestSetup()
    fts.tearDown()


def makeLayeredSuite(klass, layer):
    suite = unittest.makeSuite(klass)
    suite.layer = layer
    return suite
