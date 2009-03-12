#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2008 Shuttleworth Foundation
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
Unit tests for schooltool.generations.evolve29
"""
import unittest

from zope.app.testing import setup
from zope.testing import doctest
from zope.interface import implements

from schooltool.basicperson.person import BasicPerson
from schooltool.generations.tests import ContextStub
from schooltool.app.interfaces import ISchoolToolApplication


class AppStub(dict):
    implements(ISchoolToolApplication)

    def __init__(self):
        self['persons'] = {}
        self['persons']['john'] = BasicPerson("john", "Johny", "John")
        self['persons']['john'].email = "john@example.com"
        self['persons']['john'].phone = "667755"

        self['persons']['pete'] = BasicPerson("pete", "Petey", "Pete")
        self['persons']['pete'].email = "pete@example.com"
        self['persons']['pete'].phone = "667755"


def doctest_evolve29():
    """Evolution to generation 29.

        >>> context = ContextStub()
        >>> context.root_folder['app'] = app = AppStub()

    We set up some persons and evolve the application

        >>> from schooltool.generations.evolve29 import evolve
        >>> evolve(context)

    and the extra attributes are gone

        >>> for username, person in sorted(app['persons'].items()):
        ...     print person.__dict__
        {'username': 'john', 'first_name': 'Johny', 'last_name': 'John'}
        {'username': 'pete', 'first_name': 'Petey', 'last_name': 'Pete'}

    """


def setUp(test):
    setup.placelessSetUp()


def tearDown(test):
    setup.placelessTearDown()


def test_suite():
    return doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                optionflags=doctest.ELLIPSIS
                                |doctest.REPORT_ONLY_FIRST_FAILURE)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
