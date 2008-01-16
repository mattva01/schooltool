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
Unit tests for schooltool.app.rest.app.

$Id$
"""
import unittest

from zope.publisher.browser import TestRequest
from zope.testing import doctest
from zope.app.testing import setup

from schooltool.testing import setup as sbsetup


def doctest_ApplicationView():
    """SchoolToolApplication

    Lets create a schooltool instance and make a view for it:

        >>> from schooltool.app.rest.app import ApplicationView
        >>> setup.placefulSetUp()
        >>> app = sbsetup.setUpSchoolToolSite()
        >>> view = ApplicationView(app, TestRequest())
        >>> result = view.GET()

    Lets test the XML output:

        >>> from schooltool.common.xmlparsing import LxmlDocument
        >>> doc = LxmlDocument(result)
        >>> nsmap = {'xlink': 'http://www.w3.org/1999/xlink'}
        >>> type_attr = '{http://www.w3.org/1999/xlink}type'
        >>> title_attr = '{http://www.w3.org/1999/xlink}title'

    There should only be one set of containers:

        >>> nodes = doc.xpath('/schooltool/containers')
        >>> len(nodes)
        1

    Let's test our containers:

    persons:

        >>> persons = doc.xpath('/schooltool/containers/container'
        ...                     '[@xlink:href="http://127.0.0.1/persons"]', nsmap)[0]
        >>> persons.attrib[type_attr]
        'simple'
        >>> persons.attrib[title_attr]
        'persons'

    groups:

        >>> groups = doc.xpath('/schooltool/containers/container'
        ...                    '[@xlink:href="http://127.0.0.1/groups"]', nsmap)[0]
        >>> groups.attrib[type_attr]
        'simple'
        >>> groups.attrib[title_attr]
        'groups'

    resources:

        >>> resources = doc.xpath('/schooltool/containers/container'
        ...                       '[@xlink:href="http://127.0.0.1/resources"]', nsmap)[0]
        >>> resources.attrib[type_attr]
        'simple'
        >>> resources.attrib[title_attr]
        'resources'

    sections:

        >>> sections = doc.xpath('/schooltool/containers/container'
        ...                      '[@xlink:href="http://127.0.0.1/sections"]', nsmap)[0]
        >>> sections.attrib[type_attr]
        'simple'
        >>> sections.attrib[title_attr]
        'sections'

    courses:

        >>> courses = doc.xpath('/schooltool/containers/container'
        ...                     '[@xlink:href="http://127.0.0.1/courses"]', nsmap)[0]
        >>> courses.attrib[type_attr]
        'simple'
        >>> courses.attrib[title_attr]
        'courses'

    that's all of our containers:

    XXX this is what our output should look like:

    XXX mg: who wrote the XXX above, and what does it mean?

    Cleanup:

        >>> setup.placefulTearDown()

    """


def test_suite():
    return unittest.TestSuite([
        doctest.DocTestSuite(optionflags=doctest.ELLIPSIS),
        doctest.DocTestSuite('schooltool.app.rest.app',
                             optionflags=doctest.ELLIPSIS),
        ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
