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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Unit tests for schooltool.generations.evolve32
"""
import unittest
import doctest

from pprint import pprint
from zope.app.testing import setup
from zope.interface import implements
from zope.container import btree

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.generations.tests import ContextStub
import schooltool.basicperson.interfaces
import schooltool.basicperson.demographics
from schooltool import basicperson


class AppStub(btree.BTreeContainer):
    implements(ISchoolToolApplication)


def doctest_evolve32():
    """Evolution to generation 32.

        >>> context = ContextStub()
        >>> context.root_folder['app'] = app = AppStub()

    Create demographics with the typo (assume that user deleted or otherwise
    modified some of the demographics).

        >>> fields = basicperson.demographics.DemographicsFields()
        >>> app['schooltool.basicperson.demographics_fields'] = fields

        >>> fields['ID'] = basicperson.demographics.TextFieldDescription(
        ...     'ID', 'ID')
        >>> fields['birth'] = basicperson.demographics.TextFieldDescription(
        ...     'birth', 'Place of birth')

        >>> fields['ethnic'] = basicperson.demographics.EnumFieldDescription(
        ...     'ethnic', 'Ethnicity')
        >>> fields['ethnic'].items = [
        ...     u'Outter space',
        ...     u'Native Hawaiian or Other Pasific Islander',
        ...     u'Asian']

    Let's evolve now.

        >>> from schooltool.generations.evolve32 import evolve
        >>> evolve(context)

    The typo is fixed.

        >>> pprint(fields['ethnic'].items)
        [u'Outter space',
         u'Native Hawaiian or Other Pacific Islander',
         u'Asian']

    """


def setUp(test):
    setup.placelessSetUp()
    setup.setUpAnnotations()

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
