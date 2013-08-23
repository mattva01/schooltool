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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Unit tests for schooltool.app.browser.csvimport
"""
import unittest
import doctest

from zope.i18n import translate

from schooltool.app.browser.testing import setUp as testSetUp, tearDown

__metaclass__ = type


def doctest_BaseCSVImporter():
    r"""Test for BaseCSVImporter

    Set up

        >>> from schooltool.app.browser.csvimport import BaseCSVImporter
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

    parseCSVRows can also set errors should they occur

        >>> data = ["one, \xff"]
        >>> importer.charset = 'UTF-8'
        >>> importer.parseCSVRows(data)
        >>> translate(importer.errors.generic[0])
        u'Conversion to unicode failed in line 1'

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
        >>> translate(myimporter.errors.generic[0])
        u'Conversion to unicode failed in line 2'

    """


def doctest_ImportErrorCollection():
    r"""
    Make the class

        >>> from schooltool.app.browser.csvimport import ImportErrorCollection
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


def setUp(test=None):
    testSetUp(test)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(
        setUp=setUp, tearDown=tearDown,
        optionflags=doctest.ELLIPSIS|doctest.REPORT_NDIFF))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
