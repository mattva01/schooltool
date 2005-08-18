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
Tests for group views.

$Id: test_app.py 4691 2005-08-12 18:59:44Z srichter $
"""
import unittest
from zope.publisher.browser import TestRequest
from zope.testing import doctest

from schooltool.app.browser.testing import setUp, tearDown

def doctest_ResourceView():
    r"""Test for ResourceView

    Let's create a view for a resource:

        >>> from schooltool.resource.browser.resource import ResourceView
        >>> from schooltool.resource.resource import Resource
        >>> resource = Resource()
        >>> request = TestRequest()
        >>> view = ResourceView(resource, request)

    """


def doctest_ResourceCSVImporter():
    r"""Tests for ResourceCSVImporter.

    Create a resource container and an importer

        >>> from schooltool.resource.browser.csvimport import \
        ...     ResourceCSVImporter
        >>> from schooltool.resource.resource import ResourceContainer
        >>> container = ResourceContainer()
        >>> importer = ResourceCSVImporter(container, None)

    Import some sample data

        >>> csvdata='''Resource 1, Resource 1 Description
        ... Resource2
        ... Resource3, Resource 3 Description, location
        ... Resource4, , location'''
        >>> importer.importFromCSV(csvdata)
        True

    Check that the resources exist

        >>> [resource for resource in container]
        [u'resource-1', u'resource2', u'resource3', u'resource4']

    Check that descriptions were imported properly

        >>> [resource.description for resource in container.values()]
        ['Resource 1 Description', '', 'Resource 3 Description', '']
        >>> [resource.isLocation for resource in container.values()]
        [False, False, True, True]

    """

def doctest_ResourceCSVImportView():
    r"""
    We'll create a resource csv import view

        >>> from schooltool.resource.browser.csvimport import \
        ...     ResourceCSVImportView
        >>> from schooltool.resource.resource import ResourceContainer
        >>> container = ResourceContainer()
        >>> request = TestRequest()

    Now we'll try a text import.  Note that the description is not required

        >>> request.form = {'csvtext' : "A Resource, The best Resource\nAnother Resource",
        ...                 'charset' : 'UTF-8',
        ...                 'UPDATE_SUBMIT': 1}
        >>> view = ResourceCSVImportView(container, request)
        >>> view.update()
        >>> [resource for resource in container]
        [u'a-resource', u'another-resource']

    If no data is provided, we naturally get an error

        >>> request.form = {'charset' : 'UTF-8', 'UPDATE_SUBMIT': 1}
        >>> view.update()
        >>> view.errors
        [u'No data provided']

    We also get an error if a line starts with a comma (no title)

        >>> request.form = {'csvtext' : ", No title provided here",
        ...                 'charset' : 'UTF-8',
        ...                 'UPDATE_SUBMIT': 1}
        >>> view = ResourceCSVImportView(container, request)
        >>> view.update()
        >>> view.errors
        [u'Failed to import CSV text', u'Titles may not be empty']

    """



def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                       optionflags=doctest.ELLIPSIS|
                                                   doctest.REPORT_NDIFF))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
