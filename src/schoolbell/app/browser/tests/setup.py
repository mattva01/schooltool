"""
Setup code for SchoolBell unit tests.
"""

import os.path
from zope.interface import directlyProvides, implements
from zope.app.testing import setup, ztapi
from zope.app.session.session import ClientId, Session
from zope.app.session.session import PersistentSessionDataContainer
from zope.publisher.interfaces import IRequest
from zope.app.session.http import CookieClientIdManager
from zope.app.session.interfaces import ISessionDataContainer
from zope.app.session.interfaces import IClientId
from zope.app.session.interfaces import IClientIdManager, ISession
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

from schoolbell.relationship.tests import setUpRelationships
from schoolbell.app.browser import SchoolBellAPI, SortBy
from schoolbell.app.browser import NavigationView


def setUpSessions():
    """Set up the session machinery.

    Do this after placelessSetUp().
    """
    ztapi.provideAdapter(IRequest, IClientId, ClientId)
    ztapi.provideAdapter(IRequest, ISession, Session)
    ztapi.provideUtility(IClientIdManager, CookieClientIdManager())
    sdc = PersistentSessionDataContainer()
    ztapi.provideUtility(ISessionDataContainer, sdc)


def setUpSchoolBellSite():
    """Set up a schoolbell site.

    Do this after placelessSetup().
    """
    from schoolbell.app.app import SchoolBellApplication
    from schoolbell.app.security import setUpLocalAuth
    app = SchoolBellApplication()
    directlyProvides(app, IContainmentRoot)
    setUpLocalAuth(app)
    setSite(app)
    return app

class BrowserMenuStub(object):
    """A stub that fakes browser menu.

    So we could display schoolbell_actions menu in unit tests.
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
    """Set up the test fixture for schoolbell.app.browser doctests.

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

    # schoolbell: namespace in tal
    ztapi.provideAdapter(None, IPathAdapter, SchoolBellAPI, 'schoolbell')

    # sortby: namespace in tal
    ztapi.provideAdapter(None, IPathAdapter, SchoolBellAPI, 'schoolbell')
    ztapi.provideAdapter(None, IPathAdapter, SortBy, 'sortby')

    # standard_macros and schoolbell_navigation
    ztapi.browserView(None, 'standard_macros', StandardMacros)
    ztapi.browserView(None, 'view_macros',
                      SimpleViewClass("../templates/view_macros.pt"))
    ztapi.browserView(None, 'schoolbell_navigation',
                      SimpleViewClass("../templates/navigation.pt",
                                      bases=(NavigationView,)))

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

    for name in ['layout.css', 'style.css', 'schoolbell.js', 'logo.png',
                 'next.png', 'prev.png', 'favicon.ico']:
        ztapi.browserResource(name, ResourceStub)

    # menus
    ztapi.browserView(None, 'view_get_menu', MenuAccessView)
    ztapi.provideUtility(IBrowserMenu, BrowserMenuStub('zmi_views'), 'zmi_views')
    ztapi.provideUtility(IBrowserMenu, BrowserMenuStub('schoolbell_actions'), 'schoolbell_actions')


def tearDown(test=None):
    """Tear down the test fixture for schoolbell.app.browser doctests."""
    setup.placefulTearDown()

