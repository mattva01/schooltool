#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2004 Shuttleworth Foundation
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
Unit tests for schoolbell.app.browser.csvimport

$Id$
"""

import unittest

from zope.testing import doctest
from zope.publisher.browser import TestRequest

from schoolbell.app.browser.tests.setup import setUp, tearDown

__metaclass__ = type


def doctest_BaseCSVImporter():
    r"""Test for BaseCSVImporter

    Set up

        >>> from schoolbell.app.browser.csvimport import BaseCSVImporter
        >>> importer = BaseCSVImporter(None)

    Subclasses need to define the createAndAdd method

        >>> importer.createAndAdd(None)
        Traceback (most recent call last):
        ...
        NotImplementedError: Please override this method in subclasses

    When given a list of CSV rows parseCSVRows should return a list of lists

        >>> data = ["one, two, three", "four, five, six"]
        >>> importer.parseCSVRows(data)
        [['one', 'two', 'three'], ['four', 'five', 'six']]

    parseCSVRows can also set errors should they occour

        >>> data = ["one, \xff"]
        >>> importer.charset = 'UTF-8'
        >>> importer.parseCSVRows(data)
        >>> importer.errors.generic
        [u'Conversion to unicode failed in line 1']

    Moving on, importFromCSV calls createAndAdd which we have not defined

        >>> csvdata = "one, two, three\nfour, five, six"
        >>> importer.importFromCSV(csvdata)
        Traceback (most recent call last):
        ...
        NotImplementedError: Please override this method in subclasses

    We need to make a subclass to test this properly

        >>> class TestCSVImporter(BaseCSVImporter):
        ...     def __init__(self):
        ...         BaseCSVImporter.__init__(self, None, 'UTF-8')
        ...     def createAndAdd(self, data, True):
        ...         pass

        >>> myimporter = TestCSVImporter()

    importFromCSV just returns True if everything goes well

        >>> myimporter.importFromCSV(csvdata)
        True

    False is returned if there are errors

        >>> myimporter.importFromCSV("one, two\nthree, \xff")
        False
        >>> myimporter.errors.generic
        [u'Conversion to unicode failed in line 2']

    """

def doctest_GroupCSVImporter():
    r"""Tests for GroupCSVImporter.

    Create a group container and an importer

        >>> from schoolbell.app.browser.csvimport import GroupCSVImporter
        >>> from schoolbell.app.app import GroupContainer
        >>> container = GroupContainer()
        >>> importer = GroupCSVImporter(container, None)

    Import some sample data

        >>> csvdata='''Group 1, Group 1 Description
        ... Group2
        ... Group3, Group 3 Description, Some extra data'''
        >>> importer.importFromCSV(csvdata)
        True

    Check that the groups exist

        >>> [group for group in container]
        [u'group-1', u'group2', u'group3']

    Check that descriptions were imported properly

        >>> [group.description for group in container.values()]
        ['Group 1 Description', '', 'Group 3 Description']

    """

def doctest_GroupCSVImportView():
    r"""
    We'll create a group csv import view

        >>> from schoolbell.app.browser.csvimport import GroupCSVImportView
        >>> from schoolbell.app.app import GroupContainer
        >>> from zope.publisher.browser import TestRequest
        >>> container = GroupContainer()
        >>> request = TestRequest()

    Now we'll try a text import.  Note that the description is not required

        >>> request.form = {'csvtext' : "A Group, The best Group\nAnother Group",
        ...                 'charset' : 'UTF-8',
        ...                 'UPDATE_SUBMIT': 1}
        >>> view = GroupCSVImportView(container, request)
        >>> view.update()
        >>> [group for group in container]
        [u'a-group', u'another-group']

    If no data is provided, we naturally get an error

        >>> request.form = {'charset' : 'UTF-8', 'UPDATE_SUBMIT': 1}
        >>> view.update()
        >>> view.errors
        [u'No data provided']

    We also get an error if a line starts with a comma (no title)

        >>> request.form = {'csvtext' : ", No title provided here",
        ...                 'charset' : 'UTF-8',
        ...                 'UPDATE_SUBMIT': 1}
        >>> view = GroupCSVImportView(container, request)
        >>> view.update()
        >>> view.errors
        [u'Failed to import CSV text', u'Titles may not be empty']

    """

def doctest_ImportErrorCollection():
    r"""
    Make the class

        >>> from schoolbell.app.browser.csvimport import ImportErrorCollection
        >>> errors = ImportErrorCollection()
        >>> errors
        <ImportErrorCollection {'generic': [], 'fields': []}>

    anyErrors returns True if there are errors and False if not

        >>> errors.anyErrors()
        False
        >>> errors.fields.append('A Sample Error Message')
        >>> errors.anyErrors()
        True

    """

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                       optionflags=doctest.ELLIPSIS|
                                                   doctest.REPORT_NDIFF))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
