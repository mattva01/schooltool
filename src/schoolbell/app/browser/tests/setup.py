"""
Setup code for SchoolBell unit tests.
"""

from zope.interface import directlyProvides
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
from zope.app.traversing.interfaces import ITraversable
from zope.app.traversing.namespace import view, resource
from zope.app.traversing.interfaces import IPathAdapter
from zope.app.pagetemplate.simpleviewclass import SimpleViewClass
from zope.app.basicskin.standardmacros import StandardMacros
from zope.app.publisher.browser.menu import MenuAccessView
from zope.app.publisher.interfaces.browser import IMenuItemType

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
    ztapi.provideUtility(ISessionDataContainer, sdc, 'schoolbell.auth')


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
    class ResourceStub:
        def __init__(self, request):
            pass
        def __call__(self):
            return "a resource"

    ztapi.browserResource('layout.css', ResourceStub)
    ztapi.browserResource('style.css', ResourceStub)
    ztapi.browserResource('schoolbell.js', ResourceStub)
    ztapi.browserResource('logo.png', ResourceStub)

    ztapi.browserView(None, 'view_get_menu', MenuAccessView)
    class ZMIMenu(IMenuItemType): pass
    directlyProvides(ZMIMenu, IMenuItemType)
    ztapi.provideUtility(IMenuItemType, ZMIMenu, 'zmi_views')
    ztapi.provideUtility(IMenuItemType, ZMIMenu, 'schoolbell_actions')


def tearDown(test=None):
    """Tear down the test fixture for schoolbell.app.browser doctests."""
    setup.placefulTearDown()

