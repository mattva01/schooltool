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
Setup code for SchoolTool application browser unit tests

$Id$
"""
import os.path
from zope.interface import implements
from zope.app.testing import setup, ztapi
from zope.app.form.interfaces import IInputWidget
from zope.publisher.interfaces.browser import IBrowserRequest
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
from zope.app.traversing.interfaces import IContainmentRoot
from zope.app.traversing.interfaces import ITraversable
from zope.app.traversing.namespace import view, resource
from zope.app.traversing.interfaces import IPathAdapter
from zope.app.pagetemplate.simpleviewclass import SimpleViewClass
from zope.app.basicskin.standardmacros import StandardMacros
from zope.app.form.browser.macros import FormMacros
from zope.app.publisher.browser.menu import MenuAccessView
from zope.app.publisher.interfaces.browser import IMenuItemType, IBrowserMenu
from zope.app.component.hooks import setSite

from schooltool.relationship.tests import setUpRelationships
from schooltool.app.browser import SchoolToolAPI, SortBy
from schooltool.app.browser import NavigationView
from schooltool.app.browser.macros import SchoolToolMacros


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
    ztapi.provideAdapter(None, IPathAdapter, SchoolToolAPI, 'schooltool')

    # sortby: namespace in tal
    ztapi.provideAdapter(None, IPathAdapter, SortBy, 'sortby')

    # standard_macros, schooltool_macros and schooltool_navigation
    ztapi.browserView(None, 'standard_macros', StandardMacros)
    ztapi.browserView(None, 'view_macros',
                      SimpleViewClass("./templates/view_macros.pt"))

    ztapi.browserView(None, 'schooltool_macros', SchoolToolMacros)
    ztapi.browserView(None, 'calendar_macros',
                      SimpleViewClass("./templates/calendar_macros.pt"))
    ztapi.browserView(None, 'generic_macros',
                      SimpleViewClass("./templates/generic_macros.pt"))

    ztapi.browserView(None, 'schooltool_navigation',
                      SimpleViewClass("./templates/navigation.pt",
                                      bases=(NavigationView,)))

    # batching macros
    ztapi.browserView(None, 'batch_macros',
                      SimpleViewClass("../../batching/macros.pt"))

    # form macros
    ztapi.browserView(None, 'form_macros', FormMacros)
    import zope.app.form.browser
    base = zope.app.form.browser.__path__[0]
    ztapi.browserView(None, 'widget_macros',
                      SimpleViewClass(os.path.join(base, 'widget_macros.pt')))

    # resources
    class ResourceStub:
        def __init__(self, request):
            pass
        def __call__(self):
            return "a dummy resource"

    for name in ['layout.css', 'schooltool.css', 'schooltool.js',
                 'logo.png', 'next.png', 'prev.png', 'favicon.ico',
                 'calwidget-calendar.js', 'calwidget-calendar.css',
                 'calwidget-icon.gif']:
        ztapi.browserResource(name, ResourceStub)

    # menus
    ztapi.browserView(None, 'view_get_menu', MenuAccessView)
    ztapi.provideUtility(IBrowserMenu, BrowserMenuStub('zmi_views'),
                         'zmi_views')
    ztapi.provideUtility(IBrowserMenu, BrowserMenuStub('schooltool_actions'),
                         'schooltool_actions')

    # viewlet TALES namespaces
    from zope.app.pagetemplate import metaconfigure
    from zope.app.viewlet import tales
    metaconfigure.registerType('viewlets', tales.TALESViewletsExpression)
    metaconfigure.registerType('viewlet', tales.TALESViewletExpression)

    # viewlet regions
    from zope.app.viewlet.interfaces import IRegion
    from zope.app.component.interface import provideInterface
    from schooltool.app.browser import skin
    provideInterface('schooltool.app.browser.skin.HeaderRegion',
                     skin.HeaderRegion, IRegion)
    provideInterface('schooltool.app.browser.skin.JavaScriptRegion',
                     skin.JavaScriptRegion, IRegion)
    provideInterface('schooltool.app.browser.skin.CSSRegion',
                     skin.CSSRegion, IRegion)

def tearDown(test=None):
    """Tear down the test fixture for schooltool.app.browser doctests."""
    setup.placefulTearDown()

