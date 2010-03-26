#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2010 Shuttleworth Foundation
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
Unit tests for schooltool.generations.evolve34
"""
import unittest
import doctest

from zope.app.testing import setup
from zope.interface import implements
from zope.container.btree import BTreeContainer

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.email.interfaces import IEmailContainer


class AppStub(BTreeContainer):
    implements(ISchoolToolApplication)


class EmailContainerStub(BTreeContainer):
    implements(IEmailContainer)
    enabled = None
    hostname = None


def doctest_evolve34():
    """Test evolution to generation 34.

    Set some apps:

        >>> from schooltool.generations.tests import ContextStub
        >>> context = ContextStub()
        >>> context.root_folder['app1'] = app1 = AppStub()
        >>> context.root_folder['app2'] = app2 = AppStub()
        >>> context.root_folder['app3'] = app3 = AppStub()

    And email containers in them:

        >>> from schooltool.email.mail import EMAIL_KEY
        >>> container1 = app1[EMAIL_KEY] = EmailContainerStub()
        >>> container2 = app2[EMAIL_KEY] = EmailContainerStub()
        >>> container3 = app3[EMAIL_KEY] = EmailContainerStub()

    Set some 'hostname' attributes:

        >>> container1.hostname = ''
        >>> container3.hostname = 'localhost'

    Check the 'enabled' attributes:
    
        >>> getattr(container1, 'enabled', None) is None
        True
        >>> getattr(container2, 'enabled', None) is None
        True
        >>> getattr(container3, 'enabled', None) is None
        True

    Evolve:

        >>> from zope.component import provideAdapter
        >>> from schooltool.email.mail import getEmailContainer
        >>> provideAdapter(getEmailContainer, [ISchoolToolApplication],
        ...                IEmailContainer)
        >>> from schooltool.generations.evolve34 import evolve
        >>> evolve(context)

    Check the 'hostname' and 'enabled' attributes:

        >>> container1.hostname
        ''
        >>> container1.enabled
        False

        >>> getattr(container2, 'hostname', None) is None
        True
        >>> container2.enabled
        False

        >>> container3.hostname
        'localhost'
        >>> container3.enabled
        True

    """


def setUp(test):
    setup.placelessSetUp()


def tearDown(test):
    setup.placelessTearDown()


def test_suite():
    optionflags = (doctest.ELLIPSIS |
                   doctest.NORMALIZE_WHITESPACE |
                   doctest.REPORT_ONLY_FIRST_FAILURE)
    return doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                optionflags=optionflags)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
