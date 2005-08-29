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

$Id: test_app.py 3481 2005-04-21 15:28:29Z bskahan $
"""
import unittest
from pprint import pprint

from zope.i18n import translate
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

        >>> sbsetup.setupCalendaring()

        >>> from schooltool.app.app import getApplicationPreferences
        >>> from schooltool.app.interfaces import IApplicationPreferences
        >>> from schooltool.app.interfaces import ISchoolToolApplication

        >>> app = sbsetup.setupSchoolToolSite()

        >>> ztapi.provideAdapter(ISchoolToolApplication,
        ...                      IApplicationPreferences,
        ...                      getApplicationPreferences)

    Now lets create a view

        >>> from schooltool.app.browser.app import ApplicationView
        >>> request = TestRequest()
        >>> view = ApplicationView(app, request)
        >>> view.update()

        >>> request.response.getStatus()
        302
        >>> request.response.getHeaders()['Location']
        'http://127.0.0.1/calendar'

    If we change a the front page preference, we should not be redirected

        >>> IApplicationPreferences(app).frontPageCalendar = False
        >>> request = TestRequest()
        >>> view = ApplicationView(app, request)
        >>> view.update()

        >>> request.response.getStatus()
        599

    """

def doctest_ContainerView():
    r"""Test for ContainerView

    Let's create some persons to toy with in a person container:

        >>> from schooltool.app.browser.app import ContainerView
        >>> from schooltool.person.person import Person, PersonContainer
        >>> from schooltool.person.interfaces import IPerson
        >>> setup.setUpAnnotations()

        >>> personContainer = PersonContainer()
        >>> from zope.app.traversing.interfaces import IContainmentRoot
        >>> directlyProvides(personContainer, IContainmentRoot)

        >>> personContainer['pete'] = Person('pete', 'Pete Parrot')
        >>> personContainer['john'] = Person('john', 'Long John')
        >>> personContainer['frog'] = Person('frog', 'Frog Man')
        >>> personContainer['toad'] = Person('toad', 'Taodsworth')
        >>> request = TestRequest()
        >>> view = ContainerView(personContainer, request)

    After calling update, we should have a batch setup with everyone in it:

        >>> view.update()
        >>> [p.title for p in view.batch]
        ['Frog Man', 'Long John', 'Pete Parrot', 'Taodsworth']


    We can alter the batch size and starting point through the request

        >>> request.form = {'batch_start': '2',
        ...                 'batch_size': '2'}
        >>> view.update()
        >>> [p.title for p in view.batch]
        ['Pete Parrot', 'Taodsworth']

    We can search through the request:

        >>> request.form = {'SEARCH': 'frog'}
        >>> view.update()
        >>> [p.title for p in view.batch]
        ['Frog Man']

    And we can clear the search (which ignores any search value):

        >>> request.form = {'SEARCH': 'frog',
        ...                 'CLEAR_SEARCH': 'on'}
        >>> view.update()
        >>> [p.title for p in view.batch]
        ['Frog Man', 'Long John', 'Pete Parrot', 'Taodsworth']

    """

def doctest_ContainerDeleteView():
    r"""Test for ContainerDeleteView

    Let's create some persons to delete from a person container:

        >>> from schooltool.app.browser.app import ContainerDeleteView
        >>> from schooltool.person.person import Person, PersonContainer
        >>> from schooltool.person.interfaces import IPerson
        >>> setup.setUpAnnotations()

        >>> personContainer = PersonContainer()

        >>> from zope.interface import directlyProvides
        >>> from zope.app.traversing.interfaces import IContainmentRoot
        >>> directlyProvides(personContainer, IContainmentRoot)

        >>> personContainer['pete'] = Person('pete', 'Pete Parrot')
        >>> personContainer['john'] = Person('john', 'Long John')
        >>> personContainer['frog'] = Person('frog', 'Frog Man')
        >>> personContainer['toad'] = Person('toad', 'Taodsworth')
        >>> request = TestRequest()
        >>> view = ContainerDeleteView(personContainer, request)

    We should have the list of all the Ids of items that are going to
    be deleted from container:

        >>> view.listIdsForDeletion()
        []

    We must pass ids of selected people in the request:

        >>> request.form = {'delete.pete': 'on',
        ...                 'delete.john': 'on',
        ...                 'UPDATE_SUBMIT': 'Delete'}
        >>> ids = [key for key in view.listIdsForDeletion()]
        >>> ids.sort()
        >>> ids
        [u'john', u'pete']
        >>> [item.title for item in view.itemsToDelete]
        ['Long John', 'Pete Parrot']

    These two should be gone after update:

        >>> view.update()
        >>> ids = [key for key in personContainer]
        >>> ids.sort()
        >>> ids
        [u'frog', u'toad']

    And we should be redirected to the container view:

        >>> request.response.getStatus()
        302
        >>> request.response.getHeaders()['Location']
        'http://127.0.0.1'

    If we press Cancel no one should get hurt though:

        >>> request.form = {'delete.frog': 'on',
        ...                 'delete.toad': 'on',
        ...                 'CANCEL': 'Cancel'}

    You see, both our firends are still in there:

        >>> ids = [key for key in personContainer]
        >>> ids.sort()
        >>> ids
        [u'frog', u'toad']

    But we should be redirected to the container:

        >>> request.response.getStatus()
        302
        >>> request.response.getHeaders()['Location']
        'http://127.0.0.1'

    No redirection if nothing was pressed should happen:

        >>> request.form = {'delete.frog': 'on',
        ...                 'delete.toad': 'on'}
        >>> view.update()
        >>> request.response.getHeaders()['Location']
        'http://127.0.0.1'

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

        >>> app = sbsetup.setupSchoolToolSite()
        >>> persons = app['persons']

        >>> frog = Person('frog')
        >>> persons[None] = frog
        >>> frog.setPassword('pond')

    We create our view:

        >>> from schooltool.app.browser.app import LoginView
        >>> request = TestRequest()
        >>> class StubPrincipal:
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
        >>> sbsetup.setupSessions()

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

        >>> app = sbsetup.setupSchoolToolSite()
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
        >>> sbsetup.setupSessions()

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


def doctest_ACLView():
    r"""
    Set up for local grants:

        >>> from zope.app.annotation.interfaces import IAnnotatable
        >>> from zope.app.securitypolicy.interfaces import \
        ...                         IPrincipalPermissionManager
        >>> from zope.app.securitypolicy.principalpermission import \
        ...                         AnnotationPrincipalPermissionManager
        >>> setup.setUpAnnotations()
        >>> setup.setUpTraversal()
        >>> ztapi.provideAdapter(IAnnotatable, IPrincipalPermissionManager,
        ...                      AnnotationPrincipalPermissionManager)
        >>> from schooltool.app.interfaces import ISchoolToolApplication
        >>> from schooltool.app.interfaces import IApplicationPreferences
        >>> from schooltool.app.app import getApplicationPreferences
        >>> ztapi.provideAdapter(ISchoolToolApplication,
        ...                      IApplicationPreferences,
        ...                      getApplicationPreferences)

    Let's set the security policy:

        >>> from zope.security.management import setSecurityPolicy
        >>> from zope.app.securitypolicy.zopepolicy import ZopeSecurityPolicy
        >>> old = setSecurityPolicy(ZopeSecurityPolicy)

    Suppose we have a SchoolTool app:

        >>> app = sbsetup.setupSchoolToolSite()

    We have a couple of persons and groups:

        >>> from schooltool.group.group import Group
        >>> from schooltool.person.person import Person
        >>> app['persons']['1'] = Person('albert', title='Albert')
        >>> app['persons']['2'] = Person('marius', title='Marius')
        >>> app['groups']['3'] = Group('office')
        >>> app['groups']['4'] = Group('mgmt')

    We create an ACLView:

        >>> from schooltool.app.browser.app import ACLView
        >>> View = SimpleViewClass("../templates/acl.pt", bases=(ACLView, ))
        >>> request = TestRequest()
        >>> class StubPrincipal:
        ...     title = "Some user"
        ...
        >>> request.setPrincipal(StubPrincipal())
        >>> view = View(app, request)

    The view has methods to list persons:

        >>> pprint(view.persons)
        [{'perms': [], 'id': u'sb.person.albert', 'title': 'Albert'},
         {'perms': [], 'id': u'sb.person.marius', 'title': 'Marius'}]
        >>> pprint(view.groups)
        [{'perms': [], 'id': u'sb.group.3', 'title': 'office'},
         {'perms': [], 'id': u'sb.group.4', 'title': 'mgmt'}]

    If we have an authenticated group and an unauthenticated group, we
    get then as well:

        >>> from zope.app.security.interfaces import IAuthentication
        >>> from zope.app.security.interfaces import IAuthenticatedGroup
        >>> from zope.app.security.interfaces import IUnauthenticatedGroup
        >>> from zope.app.security.principalregistry \
        ...     import UnauthenticatedGroup
        >>> from zope.app.security.principalregistry \
        ...     import AuthenticatedGroup
        >>> unauthenticated = UnauthenticatedGroup('zope.unauthenticated',
        ...                                        'Unauthenticated users',
        ...                                        '')
        >>> ztapi.provideUtility(IUnauthenticatedGroup, unauthenticated)
        >>> authenticated = AuthenticatedGroup('zope.authenticated',
        ...                                    'Authenticated users',
        ...                                    '')
        >>> ztapi.provideUtility(IAuthenticatedGroup, authenticated)

        >>> from zope.app.security.principalregistry import principalRegistry
        >>> ztapi.provideUtility(IAuthentication, principalRegistry)
        >>> principalRegistry.registerGroup(unauthenticated)
        >>> principalRegistry.registerGroup(authenticated)

        >>> pprint(view.groups)
        [{'perms': [], 'id': 'zope.authenticated', 'title': u'Authenticated users'},
         {'id': 'zope.unauthenticated',
          'perms': [],
          'title': u'Unauthenticated users'},
         {'perms': [], 'id': u'sb.group.3', 'title': 'office'},
         {'perms': [], 'id': u'sb.group.4', 'title': 'mgmt'}]

    Also it knows a list of permissions to display:

        >>> pprint(view.permissions)
        [('schooltool.view', u'View'),
         ('schooltool.edit', u'Edit'),
         ('schooltool.create', u'Create new objects'),
         ('schooltool.viewCalendar', u'View calendar'),
         ('schooltool.addEvent', u'Add events'),
         ('schooltool.modifyEvent', u'Modify/delete events'),
         ('schooltool.controlAccess', u'Control access'),
         ('schooltool.manageMembership', u'Manage membership')]

    The view displays a matrix with groups and persons as rows and
    permisssions as columns:

        >>> print view()
        <BLANKLINE>
        <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
                  "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
        ...
        <form method="post" action="http://127.0.0.1">
        ...
          <h3>
              Access control for SchoolTool
          </h3>
          <fieldset>
            <legend>Permissions for Groups</legend>
        ...
            <table class="acl">
              <tr class="header">
                 <th class="principal">Group</th>
                 <th class="permission">View</th>
                 <th class="permission">Edit</th>
                 <th class="permission">Create new objects</th>
                 <th class="permission">View calendar</th>
                 <th class="permission">Add events</th>
                 <th class="permission">Modify/delete events</th>
                 <th class="permission">Control access</th>
                 <th class="permission">Manage membership</th>
              </tr>
        ...
              <tr class="odd">
                 <th class="principal">
                    office
                    <input type="hidden" value="1"
                           name="marker-sb.group.3" />
                 </th>
                 <td class="permission">
                    <input type="checkbox" name="sb.group.3"
                           value="schooltool.view" />
                 </td>
                 <td class="permission">
                    <input type="checkbox" name="sb.group.3"
                           value="schooltool.edit" />
                 </td>
                 <td class="permission">
                    <input type="checkbox" name="sb.group.3"
                           value="schooltool.create" />
                 </td>
                 <td class="permission">
                    <input type="checkbox" name="sb.group.3"
                           value="schooltool.viewCalendar" />
                 </td>
                 <td class="permission">
                    <input type="checkbox" name="sb.group.3"
                           value="schooltool.addEvent" />
                 </td>
                 <td class="permission">
                    <input type="checkbox" name="sb.group.3"
                           value="schooltool.modifyEvent" />
                 </td>
                 <td class="permission">
                    <input type="checkbox" name="sb.group.3"
                           value="schooltool.controlAccess" />
                 </td>
                 <td class="permission">
                    <input type="checkbox" name="sb.group.3"
                           value="schooltool.manageMembership" />
                 </td>
              </tr>
        ...
              <tr class="odd">
                 <th class="principal">
                    Albert
                    <input type="hidden" value="1"
                           name="marker-sb.person.albert" />
                 </th>
                 <td class="permission">
                    <input type="checkbox" name="sb.person.albert"
                           value="schooltool.view" />
                 </td>
                 <td class="permission">
                    <input type="checkbox" name="sb.person.albert"
                           value="schooltool.edit" />
                 </td>
                 <td class="permission">
                    <input type="checkbox" name="sb.person.albert"
                           value="schooltool.create" />
                 </td>
                 <td class="permission">
                    <input type="checkbox" name="sb.person.albert"
                           value="schooltool.viewCalendar" />
                 </td>
                 <td class="permission">
                    <input type="checkbox" name="sb.person.albert"
                           value="schooltool.addEvent" />
                 </td>
                 <td class="permission">
                    <input type="checkbox" name="sb.person.albert"
                           value="schooltool.modifyEvent" />
                 </td>
                 <td class="permission">
                    <input type="checkbox" name="sb.person.albert"
                           value="schooltool.controlAccess" />
                 </td>
                 <td class="permission">
                    <input type="checkbox" name="sb.person.albert"
                           value="schooltool.manageMembership" />
                 </td>
              </tr>
        ...

    If we submit a form with a checkbox marked, a user gets a grant:

        >>> request = TestRequest(form={
        ...     'marker-sb.person.albert': '1',
        ...     'marker-sb.person.marius': '1',
        ...     'marker-sb.group.3': '1',
        ...     'sb.person.albert': ['schooltool.view',
        ...                          'schooltool.edit'],
        ...     'sb.person.marius': 'schooltool.create',
        ...     'sb.group.3': 'schooltool.create',
        ...     'UPDATE_SUBMIT': 'Set'})
        >>> view = View(app, request)
        >>> result = view.update()

    Now the users should have permissions on app:

        >>> grants = IPrincipalPermissionManager(app)
        >>> grants.getPermissionsForPrincipal('sb.person.marius')
        [('schooltool.create', PermissionSetting: Allow)]
        >>> pprint(grants.getPermissionsForPrincipal('sb.person.albert'))
        [('schooltool.edit', PermissionSetting: Allow),
         ('schooltool.view', PermissionSetting: Allow)]
        >>> grants.getPermissionsForPrincipal('sb.group.3')
        [('schooltool.create', PermissionSetting: Allow)]

        >>> pprint(view.persons)
        [{'id': u'sb.person.albert',
          'perms': ['schooltool.view', 'schooltool.edit'],
          'title': 'Albert'},
         {'id': u'sb.person.marius',
          'perms': ['schooltool.create'],
          'title': 'Marius'}]
        >>> pprint(view.groups)
        [{'perms': [], 'id': 'zope.authenticated', 'title': u'Authenticated users'},
         {'id': 'zope.unauthenticated',
          'perms': [],
          'title': u'Unauthenticated users'},
         {'perms': ['schooltool.create'], 'id': u'sb.group.3', 'title': 'office'},
         {'perms': [], 'id': u'sb.group.4', 'title': 'mgmt'}]

    The view redirects to the context's default view:

        >>> request.response.getStatus()
        302
        >>> url = zapi.absoluteURL(app, request)
        >>> request.response.getHeader('Location') == url
        True

    If we render the form, we see the appropriate checkboxes checked:

        >>> request.setPrincipal(StubPrincipal())
        >>> print view()
        <BLANKLINE>
        <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
                  "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
        ...
              <tr class="odd">
                 <th class="principal">
                    office
                    <input type="hidden" value="1"
                           name="marker-sb.group.3" />
                 </th>
                 <td class="permission">
                    <input type="checkbox" name="sb.group.3"
                           value="schooltool.view" />
                 </td>
                 <td class="permission">
                    <input type="checkbox" name="sb.group.3"
                           value="schooltool.edit" />
                 </td>
                 <td class="permission">
                    <input type="checkbox" checked="checked"
                           name="sb.group.3"
                           value="schooltool.create" />
                 </td>
                 <td class="permission">
                    <input type="checkbox" name="sb.group.3"
                           value="schooltool.viewCalendar" />
                 </td>
                 <td class="permission">
                    <input type="checkbox" name="sb.group.3"
                           value="schooltool.addEvent" />
                 </td>
                 <td class="permission">
                    <input type="checkbox" name="sb.group.3"
                           value="schooltool.modifyEvent" />
                 </td>
                 <td class="permission">
                    <input type="checkbox" name="sb.group.3"
                           value="schooltool.controlAccess" />
                 </td>
                 <td class="permission">
                    <input type="checkbox" name="sb.group.3"
                           value="schooltool.manageMembership" />
                 </td>
              </tr>
        ...
              <tr class="odd">
                 <th class="principal">
                    Albert
                    <input type="hidden" value="1"
                           name="marker-sb.person.albert" />
                 </th>
                 <td class="permission">
                    <input type="checkbox" checked="checked"
                           name="sb.person.albert"
                           value="schooltool.view" />
                 </td>
                 <td class="permission">
                    <input type="checkbox" checked="checked"
                           name="sb.person.albert"
                           value="schooltool.edit" />
                 </td>
                 <td class="permission">
                    <input type="checkbox" name="sb.person.albert"
                           value="schooltool.create" />
                 </td>
                 <td class="permission">
                    <input type="checkbox" name="sb.person.albert"
                           value="schooltool.viewCalendar" />
                 </td>
                 <td class="permission">
                    <input type="checkbox" name="sb.person.albert"
                           value="schooltool.addEvent" />
                 </td>
                 <td class="permission">
                    <input type="checkbox" name="sb.person.albert"
                           value="schooltool.modifyEvent" />
                 </td>
                 <td class="permission">
                    <input type="checkbox" name="sb.person.albert"
                           value="schooltool.controlAccess" />
                 </td>
                 <td class="permission">
                    <input type="checkbox" name="sb.person.albert"
                           value="schooltool.manageMembership" />
                 </td>
              </tr>
        ...


    If we submit a form without a submit button, nothing is changed:

        >>> request = TestRequest(form={
        ...     'marker-sb.group.4': '1',
        ...     'sb.group.4': 'schooltool.addEvent',})
        >>> request.setPrincipal(StubPrincipal())
        >>> view = View(app, request)
        >>> result = view.update()

        >>> grants.getPermissionsForPrincipal('sb.person.marius')
        [('schooltool.create', PermissionSetting: Allow)]

    The user does not get redirected:

        >>> request.response.getStatus()
        599
        >>> url = zapi.absoluteURL(app, request)
        >>> request.response.getHeader('Location')


    However, if submit was clicked, unchecked permissions are revoked,
    and new ones granted:

        >>> request = TestRequest(form={
        ...     'marker-sb.person.marius': '1',
        ...     'marker-sb.group.4': '1',
        ...     'sb.group.4': 'schooltool.addEvent',
        ...     'UPDATE_SUBMIT': 'Set'})
        >>> view = View(app, request)
        >>> result = view.update()

        >>> grants.getPermissionsForPrincipal('sb.person.marius')
        []
        >>> grants.getPermissionsForPrincipal('sb.group.4')
        [('schooltool.addEvent', PermissionSetting: Allow)]

    If the marker for a particular principal is not present in the request,
    permission settings for that principal are left untouched:

        >>> grants.getPermissionsForPrincipal('sb.group.3')
        [('schooltool.create', PermissionSetting: Allow)]

    If the cancel button is hit, the changes are not applied, but the
    browser is redirected to the default view for context:

        >>> request = TestRequest(form={
        ...     'marker-sb.person.marius': '1',
        ...     'sb.person.marius': 'schooltool.editEvent',
        ...     'CANCEL': 'Cancel'})
        >>> view = View(app, request)
        >>> result = view.update()

        >>> grants.getPermissionsForPrincipal('sb.person.marius')
        []
        >>> grants.getPermissionsForPrincipal('sb.group.4')
        [('schooltool.addEvent', PermissionSetting: Allow)]

        >>> request.response.getStatus()
        302
        >>> url = zapi.absoluteURL(app, request)
        >>> request.response.getHeader('Location') == url
        True
    """

def doctest_ACLView_inheritance():
    r"""This test is to check that the ACL view deals correctly with
    the inherited permissions.  If a person has a permission due to a
    grant on some ancestor object in the containment hierarchy, the
    view should display a checked checkbox for that permission.  If
    that checkbox is unchecked, a local Deny grant should  be added.

    Set up for local grants:

        >>> from zope.app.annotation.interfaces import IAnnotatable
        >>> from zope.app.securitypolicy.interfaces import \
        ...                         IPrincipalPermissionManager
        >>> from zope.app.securitypolicy.principalpermission import \
        ...                         AnnotationPrincipalPermissionManager
        >>> setup.setUpAnnotations()
        >>> setup.setUpTraversal()
        >>> ztapi.provideAdapter(IAnnotatable, IPrincipalPermissionManager,
        ...                      AnnotationPrincipalPermissionManager)

    Suppose we have a SchoolTool app:

        >>> app = sbsetup.setupSchoolToolSite()

    We have a couple of persons and groups:

        >>> from schooltool.person.person import Person
        >>> app['persons']['1'] = Person('albert', title='Albert')
        >>> app['persons']['2'] = Person('marius', title='Marius')

    Let's set the security policy:

        >>> from zope.security.management import setSecurityPolicy
        >>> from zope.app.securitypolicy.zopepolicy import ZopeSecurityPolicy
        >>> old = setSecurityPolicy(ZopeSecurityPolicy)

    Let's set some permissions on the app object:

        >>> perms = IPrincipalPermissionManager(app)
        >>> perms.grantPermissionToPrincipal('schooltool.controlAccess',
        ...                                  'sb.person.albert')
        >>> perms.grantPermissionToPrincipal('schooltool.manageMembership',
        ...                                  'sb.person.marius')

    Let's create an ACLView on a subobject of the object that holds
    the grants:

        >>> from schooltool.app.browser.app import ACLView
        >>> View = SimpleViewClass("../templates/acl.pt", bases=(ACLView, ))
        >>> request = TestRequest()
        >>> view = View(app['persons'], request)

    Now, view.persons shows the principals have the permissions:

        >>> pprint(view.persons)
        [{'id': u'sb.person.albert',
          'perms': ['schooltool.controlAccess'],
          'title': 'Albert'},
         {'id': u'sb.person.marius',
          'perms': ['schooltool.manageMembership'],
          'title': 'Marius'}]

    Now, let's post a form that unchecked the permission for Marius,
    but left the one for Albert:

        >>> request = TestRequest(form={
        ...     'marker-sb.person.marius': '1',
        ...     'marker-sb.person.albert': '1',
        ...     'sb.person.albert': 'schooltool.controlAccess',
        ...     'UPDATE_SUBMIT': 'Set'})
        >>> view = View(app['persons'], request)
        >>> result = view.update()

    Now, Albert should have no new permissions on app['persons']:

        >>> perms = IPrincipalPermissionManager(app['persons'])
        >>> perms.getPermissionsForPrincipal('sb.person.albert')
        []

    As for Marius, he should have gotten a grant that denies the
    permission he has got from app:

        >>> perms = IPrincipalPermissionManager(app['persons'])
        >>> perms.getPermissionsForPrincipal('sb.person.marius')
        [('schooltool.manageMembership', PermissionSetting: Deny)]

    Permissions on app are unchanged (unsurprisingly):

        >>> perms = IPrincipalPermissionManager(app)
        >>> perms.getPermissionsForPrincipal('sb.person.albert')
        [('schooltool.controlAccess', PermissionSetting: Allow)]

        >>> perms = IPrincipalPermissionManager(app)
        >>> perms.getPermissionsForPrincipal('sb.person.marius')
        [('schooltool.manageMembership', PermissionSetting: Allow)]

    """

def doctest_hasPermission():
    r"""The Zope security machinery does not have tools to check
    whether a random principal has some permission on some object.  So
    we need co construct our own.

    Set up for local grants:

        >>> from zope.app.annotation.interfaces import IAnnotatable
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

        >>> app = sbsetup.setupSchoolToolSite()

    In it, we have a principal:

        >>> from schooltool.person.person import Person
        >>> app['persons']['1'] = Person('joe', title='Joe')

    He does not have a 'super' permission on our schooltool app:

        >>> from schooltool.app.browser.app import hasPermission
        >>> hasPermission('super', app, 'sb.person.joe')
        False

    However, we can add a local grant:

        >>> perms = IPrincipalPermissionManager(app)
        >>> perms.grantPermissionToPrincipal('super', 'sb.person.joe')

    Now, hasPermission returns true:

        >>> hasPermission('super', app, 'sb.person.joe')
        True

    The same works for subobjects:

        >>> hasPermission('super', app['persons'], 'sb.person.joe')
        True
        >>> hasPermission('super', app['persons']['joe'], 'sb.person.joe')
        True

    Also, it works gracefully for None or random objects:

        >>> hasPermission('super', None, 'sb.person.joe')
        False
        >>> hasPermission('super', object(), 'sb.person.joe')
        False
    """

def doctest_ApplicationPreferencesView():
    """

    We need to setup a SchoolToolApplication site and build our
    ISchoolToolApplication adapter:

        >>> app = sbsetup.setupSchoolToolSite()

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

        >>> request = TestRequest(form={'UPDATE_SUBMIT': 'Update',
        ...                             'field.title': 'Company Calendars',})
        >>> view = ApplicationPreferencesView(app, request)

        >>> view.update()

        >>> prefs = getApplicationPreferences(app)
        >>> prefs.title
        u'Company Calendars'

    """


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                       optionflags=doctest.ELLIPSIS|
                                                   doctest.REPORT_NDIFF))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
