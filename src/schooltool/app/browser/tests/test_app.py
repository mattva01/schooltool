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
Tests for schooltool views.

$Id$
"""
import unittest
from pprint import pprint

from zope.interface import directlyProvides
from zope.publisher.browser import TestRequest
from zope.testing import doctest
from zope.app import zapi
from zope.app.pagetemplate.simpleviewclass import SimpleViewClass
from zope.app.testing import setup, ztapi

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

        >>> ztapi.provideAdapter(ISchoolToolApplication,
        ...                      IApplicationPreferences,
        ...                      getApplicationPreferences)

    Now let's create a view

        >>> from schooltool.app.browser.app import ApplicationView
        >>> request = TestRequest()
        >>> view = ApplicationView(app, request)
        >>> view.update()

        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('Location')
        'http://127.0.0.1/calendar'

    If we change a the front page preference, we should not be redirected

        >>> IApplicationPreferences(app).frontPageCalendar = False
        >>> request = TestRequest()
        >>> view = ApplicationView(app, request)
        >>> view.update()

        >>> request.response.getStatus()
        599

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
        >>> ztapi.provideAdapter(IHaveCalendar, ISchoolToolCalendar,
        ...                      getCalendarWithNakedObject)

        >>> from schooltool.testing import registry
        >>> registry.setupCalendarComponents()

        >>> from schooltool.app.interfaces import ISchoolToolApplication
        >>> from schooltool.app.interfaces import IApplicationPreferences
        >>> from schooltool.app.app import getApplicationPreferences
        >>> ztapi.provideAdapter(ISchoolToolApplication,
        ...                      IApplicationPreferences,
        ...                      getApplicationPreferences)

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
        >>> from zope.app.authentication.interfaces import IPrincipal
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
        >>> from zope.app.security.interfaces import IAuthentication
        >>> auth = SchoolToolAuthenticationUtility()
        >>> ztapi.provideUtility(IAuthentication, auth)
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
        'http://127.0.0.1/persons/frog/calendar'
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
        ...                             'nexturl': 'http://host/path',
        ...                             'LOGIN': 'Log in'})
        >>> request.setPrincipal(StubPrincipal())
        >>> view = View(app, request)
        >>> content = view()
        >>> view.error
        >>> request.response.getStatus()
        302
        >>> url = zapi.absoluteURL(app, request)
        >>> request.response.getHeader('Location')
        'http://host/path'

    """


def doctest_LogoutView():
    """
    Suppose we have a SchoolTool app and a person:

        >>> app = sbsetup.setUpSchoolToolSite()
        >>> persons = app['persons']

        >>> from schooltool.person.person import Person
        >>> frog = Person('frog')
        >>> persons[None] = frog
        >>> frog.setPassword('pond')

    Also, we have an authentication utility:

        >>> from schooltool.app.security import SchoolToolAuthenticationUtility
        >>> from zope.app.security.interfaces import IAuthentication
        >>> auth = SchoolToolAuthenticationUtility()
        >>> ztapi.provideUtility(IAuthentication, auth)
        >>> auth.__parent__ = app
        >>> sbsetup.setUpSessions()

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
        >>> url = zapi.absoluteURL(app, request)
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
        >>> from zope.app.securitypolicy.interfaces import \
        ...                         IPrincipalPermissionManager
        >>> from zope.app.securitypolicy.principalpermission import \
        ...                         AnnotationPrincipalPermissionManager
        >>> setup.setUpAnnotations()
        >>> setup.setUpTraversal()
        >>> ztapi.provideAdapter(IAnnotatable, IPrincipalPermissionManager,
        ...                      AnnotationPrincipalPermissionManager)


    Let's set the Zope security policy:

        >>> from zope.security.management import setSecurityPolicy
        >>> from zope.app.securitypolicy.zopepolicy import ZopeSecurityPolicy
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
        >>> ztapi.provideAdapter(ISchoolToolApplication,
        ...                      IApplicationPreferences,
        ...                      getApplicationPreferences)

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

        >>> from zope.testing.doctestunit import pprint
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
