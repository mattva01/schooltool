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
Tests for schoolbell views.

$Id$
"""

import unittest
from zope.testing import doctest
from zope.app.tests import setup, ztapi
from zope.interface import implements, directlyProvides
from zope.app.traversing.interfaces import IContainmentRoot
from zope.publisher.browser import TestRequest


def doctest_ContainerView():
    """Tests for ContainerView.

    It is a generic class for containers that contain objects with a `title`
    attribute.

        >>> class SomeObject:
        ...     def __init__(self, title):
        ...         self.title = title
        ...     def __repr__(self):
        ...         return '<SomeObject %r>' % self.title

        >>> from schoolbell.app.browser.app import ContainerView
        >>> context = {'id1': SomeObject('orange'),
        ...            'id2': SomeObject('apple'),
        ...            'id3': SomeObject('banana')}
        >>> request = TestRequest()
        >>> view = ContainerView(context, request)

    The view defines a method called `sortedObject` so that page templates
    can display the items in alphabetical order.

        >>> view.sortedObjects()
        [<SomeObject 'apple'>, <SomeObject 'banana'>, <SomeObject 'orange'>]

    """


def doctest_PersonView():
    r"""Test for PersonView

    Let's create a view for a person:

        >>> from schoolbell.app.browser.app import PersonView
        >>> from schoolbell.app.app import Person
        >>> person = Person()
        >>> request = TestRequest()
        >>> view = PersonView(person, request)

    TODO: implement proper permission checking.
    For now, all these methods just return True

        >>> view.canEdit()
        True
        >>> view.canChangePassword()
        True
        >>> view.canViewCalendar()
        True
        >>> view.canChooseCalendars()
        True

    """


def doctest_PersonPhotoView():
    r"""Test for PersonPhotoView

    We will need a person that has a photo:

        >>> from schoolbell.app.app import Person
        >>> person = Person()
        >>> person.photo = "I am a photo!"

    We can now create a view:

        >>> from schoolbell.app.browser.app import PersonPhotoView
        >>> request = TestRequest()
        >>> view = PersonPhotoView(person, request)

    The view returns the photo and sets the appropriate Content-Type header:

        >>> view()
        'I am a photo!'
        >>> request.response.getHeader("Content-Type")
        'image/jpeg'

    However, if a person has no photo, the view raises a NotFound error.

        >>> person.photo = None
        >>> view()                                  # doctest: +ELLIPSIS
        Traceback (most recent call last):
          ...
        NotFound: Object: <...Person object at ...>, name: u'photo'

    """


def doctest_GroupView():
    r"""Test for GroupView

    Let's create a view for a group:

        >>> from schoolbell.app.browser.app import GroupView
        >>> from schoolbell.app.app import Group
        >>> group = Group()
        >>> request = TestRequest()
        >>> view = GroupView(group, request)

    TODO: implement proper permission checking.
    For now, all these methods just return True

        >>> view.canEdit()
        True

    """


def doctest_ResourceView():
    r"""Test for ResourceView

    Let's create a view for a resource:

        >>> from schoolbell.app.browser.app import ResourceView
        >>> from schoolbell.app.app import Resource
        >>> resource = Resource()
        >>> request = TestRequest()
        >>> view = ResourceView(resource, request)

    TODO: implement proper permission checking.
    For now, all these methods just return True

        >>> view.canEdit()
        True

    """


def doctest_PersonChangePasswordView():
    r"""Test for PersonChangePasswordView

    We need some setup to make widgets work in a unit test.

        >>> setUpViewsAndForms()

    PersonChangePasswordView is a view on IPerson.

        >>> from schoolbell.app.app import Person
        >>> person = Person()

    We will define a subclass because supplying principals to the Zope
    3 security mechanism is a pain.

        >>> from schoolbell.app.browser.app import PersonChangePasswordView
        >>> class TestPersonChangePasswordView(PersonChangePasswordView):
        ...    def __init__(self, context, request, pretend_to_be_manager=False):
        ...         self._pretend_to_be_manager = pretend_to_be_manager
        ...         PersonChangePasswordView.__init__(self, context, request)
        ...    def isZopeManager(self):
        ...         return self._pretend_to_be_manager

    Anonymous user:

        >>> request = TestRequest()
        >>> view = TestPersonChangePasswordView(person, request, False)

    Anonymous user can see all the fields in the form

       >>> [widget.name for widget in view.widgets()]
       ['field.old_password', 'field.new_password', 'field.verify_password']

    Anonymous user can't disable user accounts

        >>> request = TestRequest(form={'UPDATE_DISABLE': True})
        >>> view = TestPersonChangePasswordView(person, request)

        >>> view.update()
        >>> view.error
        u'You are not a manager!'

    Anonymous user can't set a person's password without providing a valid
    old password (XXX this will change when we implement Zope-level
    authentication; see also the next test snippet)

        >>> person.setPassword('lala')
        >>> request = TestRequest(form={'UPDATE_SUBMIT': True,
        ...                             'field.old_password': 'foo',
        ...                             'field.new_password': 'bar',
        ...                             'field.verify_password': 'bar'})
        >>> view = TestPersonChangePasswordView(person, request)

        >>> view.update()
        >>> view.error
        u'Wrong password!'

    Anonymous user can set a person's password when a valid password
    is provided (XXX see the XXX above)

        >>> person.setPassword('lala')
        >>> request = TestRequest(form={'UPDATE_SUBMIT': True,
        ...                             'field.old_password': 'lala',
        ...                             'field.new_password': 'bar',
        ...                             'field.verify_password': 'bar'})
        >>> view = TestPersonChangePasswordView(person, request)

        >>> view.update()
        >>> view.message
        u'Password was successfully changed!'

    That is, unless new password and confirm password do not match

        >>> person.setPassword('lala')
        >>> request = TestRequest(form={'UPDATE_SUBMIT': True,
        ...                             'field.old_password': 'lala',
        ...                             'field.new_password': 'bara',
        ...                             'field.verify_password': 'bar'})
        >>> view = TestPersonChangePasswordView(person, request)

        >>> view.update()
        >>> view.error
        u'Passwords do not match.'

    Manager user:

        >>> request = TestRequest()
        >>> view = TestPersonChangePasswordView(person, request, True)

    Manager should not see the 'old_password' field

       >>> [widget.name for widget in view.widgets()]
       ['field.new_password', 'field.verify_password']

    Manager can disable user accounts

        >>> request = TestRequest(form={'UPDATE_DISABLE': True})
        >>> view = TestPersonChangePasswordView(person, request, True)

        >>> view.update()
        >>> view.error

    Manager can set a person's password without having to provide the
    old password

        >>> person.setPassword('lala')
        >>> request = TestRequest(form={'UPDATE_SUBMIT': True,
        ...                             'field.new_password': 'bar',
        ...                             'field.verify_password': 'bar'})
        >>> view = TestPersonChangePasswordView(person, request, True)

        >>> view.update()
        >>> view.message
        u'Password was successfully changed!'

    Unless new password and confirm password do not match

        >>> person.setPassword('lala')
        >>> request = TestRequest(form={'UPDATE_SUBMIT': True,
        ...                             'field.new_password': 'bara',
        ...                             'field.verify_password': 'bar'})
        >>> view = TestPersonChangePasswordView(person, request, True)

        >>> view.update()
        >>> view.error
        u'Passwords do not match.'

    That's all.

        >>> tearDownViewsAndForms()

    """


def setUpViewsAndForms():
    from zope.app.form.browser import PasswordWidget
    from zope.app.form.interfaces import IInputWidget
    from zope.schema.interfaces import IPassword
    setup.placelessSetUp()
    # widgets
    ztapi.browserViewProviding(IPassword, PasswordWidget, IInputWidget)


def tearDownViewsAndForms():
    setup.placelessTearDown()


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite())
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
