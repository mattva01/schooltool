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
Tests for schooltool views.
"""
import unittest
import doctest

from zope.publisher.browser import TestRequest
from zope.browserpage.simpleviewclass import SimpleViewClass
from zope.app.testing import setup
from zope.traversing.browser.absoluteurl import absoluteURL
from zope.component import provideAdapter, provideUtility

from schooltool.app.browser.testing import setUp, tearDown
from schooltool.testing import setup as sbsetup


def doctest_ApplicationView():
    r"""Test for ApplicationView

    Some setup

        >>> sbsetup.setUpCalendaring()

        >>> from schooltool.app.app import getApplicationPreferences
        >>> from schooltool.app.interfaces import IApplicationPreferences
        >>> from schooltool.app.interfaces import ISchoolToolApplication

        >>> app = sbsetup.setUpSchoolToolSite()

        >>> provideAdapter(getApplicationPreferences,
        ...                (ISchoolToolApplication,), IApplicationPreferences)

    Now let's create a view

        >>> from schooltool.app.browser.app import ApplicationView
        >>> request = TestRequest()
        >>> view = ApplicationView(app, request)
        >>> view.update()

        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('Location')
        'http://127.0.0.1/calendar'

    If we change a the front page preference, we are redirected
    to the login page

        >>> IApplicationPreferences(app).frontPageCalendar = False
        >>> request = TestRequest()
        >>> view = ApplicationView(app, request)
        >>> view.update()

        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('Location')
        'http://127.0.0.1/auth/@@login.html'

    """


def doctest_LoginView():
    """

    Some framework setup:

        >>> setup.setUpAnnotations()

        >>> def getCalendarWithNakedObject(obj):
        ...     from schooltool.app.cal import getCalendar
        ...     from zope.security.proxy import removeSecurityProxy
        ...     return getCalendar(removeSecurityProxy(obj))

        >>> from schooltool.app.interfaces import IHaveCalendar
        >>> from schooltool.app.interfaces import ISchoolToolCalendar
        >>> provideAdapter(getCalendarWithNakedObject,
        ...                (IHaveCalendar,), ISchoolToolCalendar)

        >>> from schooltool.testing import registry
        >>> registry.setupCalendarComponents()

        >>> from schooltool.app.interfaces import ISchoolToolApplication
        >>> from schooltool.app.interfaces import IApplicationPreferences
        >>> from schooltool.app.app import getApplicationPreferences
        >>> provideAdapter(getApplicationPreferences,
        ...                (ISchoolToolApplication,), IApplicationPreferences)

    We have to set up a security checker for person objects:

        >>> from schooltool.person.person import Person
        >>> from zope.security.checker import defineChecker, Checker
        >>> defineChecker(Person, Checker({},{}))

    Suppose we have a SchoolTool app and a person:

        >>> app = sbsetup.setUpSchoolToolSite()
        >>> persons = app['persons']

        >>> frog = Person('frog')
        >>> persons[None] = frog
        >>> frog.setPassword('pond')

    We create our view:

        >>> from schooltool.app.browser.app import LoginView
        >>> request = TestRequest()
        >>> from zope.security.interfaces import IPrincipal
        >>> from zope.interface import implements
        >>> class StubPrincipal(object):
        ...     implements(IPrincipal)
        ...     title = "Some user"
        ...
        >>> request.setPrincipal(StubPrincipal())
        >>> View = SimpleViewClass('../templates/login.pt', bases=(LoginView,))
        >>> view = View(app, request)

    Render it with an empty request:

        >>> content = view()
        >>> '<h3>Please log in</h3>' in content
        True

    If we have authentication utility:

        >>> from schooltool.app.security import SchoolToolAuthenticationUtility
        >>> from zope.authentication.interfaces import IAuthentication
        >>> auth = SchoolToolAuthenticationUtility()
        >>> provideUtility(auth, IAuthentication)

        >>> from schooltool.app.security import PersonContainerAuthenticationPlugin
        >>> plugin = PersonContainerAuthenticationPlugin()
        >>> provideUtility(plugin)

        >>> auth.__parent__ = app
        >>> sbsetup.setUpSessions()

    It does not authenticate our session:

        >>> auth.authenticate(request)

    However, if we pass valid credentials, we get authenticated:

        >>> request = TestRequest(form={'username': 'frog',
        ...                             'password': 'pond',
        ...                             'LOGIN': 'Log in'})
        >>> request.setPrincipal(StubPrincipal())
        >>> view = View(app, request)
        >>> content = view()
        >>> view.error
        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('Location')
        'http://127.0.0.1/persons/frog/@@logindispatch'
        >>> auth.authenticate(request)
        <schooltool.app.security.Principal object at 0x...>

    If we pass bad credentials, we get a nice error and a form.

        >>> request = TestRequest(form={'username': 'snake',
        ...                             'password': 'pw',
        ...                             'LOGIN': 'Log in'})
        >>> auth.setCredentials(request, 'frog', 'pond')
        >>> request.setPrincipal(auth.authenticate(request))
        >>> view = View(app, request)
        >>> content = view()
        >>> view.error
        u'Username or password is incorrect'
        >>> view.error in content
        True
        >>> 'Please log in' in content
        True

    The previous credentials are not lost if a new login fails:

        >>> principal = auth.authenticate(request)
        >>> principal
        <schooltool.app.security.Principal object at 0x...>
        >>> principal.id
        'sb.person.frog'

    We can specify the URL we want to go to after being authenticated:

        >>> request = TestRequest(form={'username': 'frog',
        ...                             'password': 'pond',
        ...                             'nexturl': 'http://127.0.0.1/path',
        ...                             'LOGIN': 'Log in'})
        >>> request.setPrincipal(StubPrincipal())
        >>> view = View(app, request)
        >>> content = view()
        >>> view.error
        >>> request.response.getStatus()
        302
        >>> url = absoluteURL(app, request)
        >>> request.response.getHeader('Location')
        'http://127.0.0.1/path'

    But we cannot specify a different server.
        >>> request = TestRequest(form={'username': 'frog',
        ...                             'password': 'pond',
        ...                             'nexturl': 'http://FAKE/path',
        ...                             'LOGIN': 'Log in'})
        >>> request.setPrincipal(StubPrincipal())
        >>> view = View(app, request)
        >>> content = view()
        Traceback (most recent call last):
        ...
        ValueError: Untrusted redirect to host '...' not allowed.

    """


def doctest_LogoutView():
    """
    Suppose we have a SchoolTool app and a person:

        >>> from schooltool.app.interfaces import ISchoolToolApplication
        >>> from zope.component import provideAdapter
        >>> app = sbsetup.setUpSchoolToolSite()
        >>> persons = app['persons']
        >>> provideAdapter(lambda context: app, adapts=[None],
        ...                provides=ISchoolToolApplication)

        >>> from schooltool.person.person import Person
        >>> frog = Person('frog')
        >>> persons[None] = frog
        >>> frog.setPassword('pond')

    Also, we have an authentication utility:

        >>> from schooltool.app.security import SchoolToolAuthenticationUtility
        >>> from zope.authentication.interfaces import IAuthentication
        >>> auth = SchoolToolAuthenticationUtility()
        >>> provideUtility(auth, IAuthentication)
        >>> auth.__parent__ = app
        >>> sbsetup.setUpSessions()

        >>> from schooltool.app.security import PersonContainerAuthenticationPlugin
        >>> plugin = PersonContainerAuthenticationPlugin()
        >>> provideUtility(plugin)

    We have a request in an authenticated session:

        >>> request = TestRequest()
        >>> auth.setCredentials(request, 'frog', 'pond')
        >>> request.setPrincipal(auth.authenticate(request))

    And we call the logout view:

        >>> from schooltool.app.browser.app import LogoutView
        >>> view = LogoutView(app, request)
        >>> view()

    Now, the session no longer has an authenticated user:

        >>> auth.authenticate(request)

    The user gets redirected to the front page:

        >>> request.response.getStatus()
        302
        >>> url = absoluteURL(app, request)
        >>> request.response.getHeader('Location') == url
        True


    The view also doesn't fail if the user was not logged in in the
    first place:

        >>> request = TestRequest()
        >>> view = LogoutView(app, request)
        >>> view()
        >>> auth.authenticate(request)

    """


def doctest_hasPermissions():
    r"""The Zope security machinery does not have tools to check
    whether a random principal has some permission on some object.  So
    we need to construct our own.

    Set up for local grants:

        >>> from zope.annotation.interfaces import IAnnotatable
        >>> from zope.securitypolicy.interfaces import \
        ...                         IPrincipalPermissionManager
        >>> from zope.securitypolicy.principalpermission import \
        ...                         AnnotationPrincipalPermissionManager
        >>> setup.setUpAnnotations()
        >>> setup.setUpTraversal()
        >>> provideAdapter(AnnotationPrincipalPermissionManager,
        ...                (IAnnotatable,), IPrincipalPermissionManager)

    Let's set the Zope security policy:

        >>> from zope.security.management import setSecurityPolicy
        >>> from zope.securitypolicy.zopepolicy import ZopeSecurityPolicy
        >>> old = setSecurityPolicy(ZopeSecurityPolicy)

    Suppose we have a SchoolTool object:

        >>> app = sbsetup.setUpSchoolToolSite()

    In it, we have a principal:

        >>> from schooltool.person.person import Person
        >>> app['persons']['1'] = Person('joe', title='Joe')

    He does not have neither 'super' nor 'duper' permissions on our
    schooltool app:

        >>> from schooltool.app.browser.app import hasPermissions
        >>> hasPermissions(['super', 'duper'], app, 'sb.person.joe')
        [False, False]

    However, we can add a local grant:

        >>> perms = IPrincipalPermissionManager(app)
        >>> perms.grantPermissionToPrincipal('super', 'sb.person.joe')

    And everything changes!

        >>> hasPermissions(['super', 'duper'], app, 'sb.person.joe')
        [True, False]

    The same works for subobjects:

        >>> hasPermissions(['duper', 'super'], app['persons'], 'sb.person.joe')
        [False, True]
        >>> hasPermissions(['super', 'duper'], app['persons']['joe'], 'sb.person.joe')
        [True, False]

    Also, it works gracefully for None or random objects:

        >>> hasPermissions(['super'], None, 'sb.person.joe')
        [False]
        >>> hasPermissions(['super'], object(), 'sb.person.joe')
        [False]

    """


def doctest_ApplicationPreferencesView():
    """Test for ApplicationPreferencesView.

    We need to setup a SchoolToolApplication site and build our
    ISchoolToolApplication adapter:

        >>> app = sbsetup.setUpSchoolToolSite()

        >>> from schooltool.app.browser.app import ApplicationPreferencesView
        >>> from schooltool.app.app import getApplicationPreferences
        >>> from schooltool.app.interfaces import IApplicationPreferences
        >>> from schooltool.app.interfaces import ISchoolToolApplication

        >>> setup.setUpAnnotations()
        >>> provideAdapter(getApplicationPreferences,
        ...                (ISchoolToolApplication,), IApplicationPreferences)

    Make sure we can create a view:

        >>> request = TestRequest()
        >>> view = ApplicationPreferencesView(app, request)

    Now we can setup a post and set the site title:

        >>> request = TestRequest(form={
        ...     'UPDATE_SUBMIT': 'Update',
        ...     'field.title': 'Company Calendars',
        ...     'field.dateformat': '%m/%d/%y',
        ...     'field.timeformat': '%I:%M %p',
        ...     'field.weekstart': '0',
        ...     'field.timezone': 'GMT'})
        >>> view = ApplicationPreferencesView(app, request)

        >>> view.update()

        >>> prefs = getApplicationPreferences(app)
        >>> prefs.title
        u'Company Calendars'

        >>> prefs.dateformat
        '%m/%d/%y'

        >>> prefs.timeformat
        '%I:%M %p'

        >>> prefs.weekstart
        0

        >>> prefs.timezone
        'GMT'

    """


def doctest_RelationshipViewBase():
    """Test for RelationshipViewBase.

    Let's create the view first:

        >>> from schooltool.app.browser.app import RelationshipViewBase
        >>> from zope.publisher.browser import TestRequest
        >>> request = TestRequest()
        >>> view = RelationshipViewBase(None, request)

    Update method of our view should process the form and perform
    necessary actions, like add items to the collections and most
    importantly to set up available and selected item tables:

        >>> from pprint import pprint
        >>> def FakeTableSetUp(**kwargs):
        ...     print "Setting up table:"
        ...     pprint(kwargs)
        >>> view.createTableFormatter = FakeTableSetUp
        >>> view.getAvailableItems = lambda: "<Available Items>"
        >>> view.getSelectedItems = lambda: "<Selected Items>"
        >>> view.update()
        Setting up table: {'ommit': '<Selected Items>',
                           'prefix': 'add_item'}
        Setting up table: {'batch_size': 0,
                           'filter': <function <lambda> at ...>,
                           'items': '<Selected Items>',
                           'prefix': 'remove_item'}

    """


def doctest_ContentTitle():
    """Tests for ContentTitle.

        >>> from schooltool.app.browser.app import ContentTitle

        >>> class ContentStub(object):
        ...     title='Foo'

        >>> provider = ContentTitle(ContentStub(), TestRequest(), None)
        >>> print provider()
        Foo

    """


def doctest_ContentLink():
    """Tests for ContentLink.

        >>> from schooltool.app.browser.app import ContentLink

        >>> class ContentStub(object):
        ...     title='Foo'

        >>> app = sbsetup.createSchoolToolApplication()
        >>> app['content'] = ContentStub()

        >>> provider = ContentLink(app['content'], TestRequest(), None)
        >>> print provider()
        <a href="http://127.0.0.1/content">Foo</a>

    """


def doctest_ContentLabel():
    """Tests for ContentLabel.

        >>> from schooltool.app.browser.app import ContentLabel

        >>> class ContentStub(object):
        ...     title='Foo'

        >>> app = sbsetup.createSchoolToolApplication()
        >>> app['content'] = ContentStub()

        >>> provider = ContentLabel(app['content'], TestRequest(), None)
        >>> print provider()
        <a href="http://127.0.0.1/content">Foo</a>

        >>> app['content'].label = 'This is the Foo!'
        >>> print provider()
        <a href="http://127.0.0.1/content">This is the Foo!</a>

    """


def test_suite():
    optionflags = (doctest.ELLIPSIS | doctest.REPORT_NDIFF
                   | doctest.REPORT_ONLY_FIRST_FAILURE
                   | doctest.NORMALIZE_WHITESPACE)
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                       optionflags=optionflags))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
