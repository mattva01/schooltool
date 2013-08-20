#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2006 Shuttleworth Foundation
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
Tests for customisation of SchoolTool security policy.
"""
import unittest
import doctest

from zope.interface import implements
from zope.publisher.browser import TestRequest


def doctest_AccessControlView():
    r"""Tests for AccessControlView.

    The view should display a list of all settings provided by the
    AccessControlCustomisations of the SchoolToolApplication:

        >>> from schooltool.app.interfaces import ISchoolToolApplication
        >>> from schooltool.securitypolicy.interfaces import IAccessControlCustomisations
        >>> class CustomisationsStub(object):
        ...     implements(IAccessControlCustomisations)
        ...     def __iter__(self):
        ...         return iter(['Access', 'control', 'settings'])

        >>> class AppStub(object):
        ...     implements(ISchoolToolApplication)
        ...     def __conform__(self, iface):
        ...         if iface == IAccessControlCustomisations:
        ...             return CustomisationsStub()

        >>> from zope.component import provideAdapter
        >>> provideAdapter(lambda context: AppStub(),
        ...                adapts=[None],
        ...                provides=ISchoolToolApplication)

        >>> from schooltool.securitypolicy.browser.views import AccessControlView
        >>> view = AccessControlView(None, None)
        >>> view.settings()
        ['Access', 'control', 'settings']

    """


def doctest_AccessControlView_update():
    """Tests for AccessControlView.update()

        >>> from schooltool.securitypolicy.browser.views import AccessControlView
        >>> request = TestRequest()
        >>> view = AccessControlView(None, request)

    If there is nothing in the form, update does nothing:

        >>> view.update()

    If we click on Update, it should update all the settings with data
    in the form:

        >>> class SettingStub(object):
        ...     def __init__(self, key):
        ...         self.key = key
        ...     def setValue(self, value):
        ...         print "Setting value of '%s' to '%s'" % (self.key, value)
        >>> view.settings = lambda: [SettingStub('one'), SettingStub('two')]
        >>> request.form = {'UPDATE_SUBMIT': '', 'setting.one': 'checked'}
        >>> view.update()
        Setting value of 'one' to 'True'
        Setting value of 'two' to 'False'

    """


def test_suite():
    return unittest.TestSuite([
            doctest.DocTestSuite(optionflags=doctest.ELLIPSIS |
                                             doctest.NORMALIZE_WHITESPACE)])

