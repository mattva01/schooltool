#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2007 Shuttleworth Foundation
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
Unit tests for person xml views.
"""
import unittest
import doctest

from zope.app.testing import setup
from zope.component import provideAdapter
from zope.interface import Interface
from zope.interface import implements
from zope.interface.verify import verifyObject
from zope.publisher.browser import BrowserView
from zope.publisher.browser import TestRequest
from zope.publisher.interfaces.browser import IBrowserRequest


def setUp(test):
    setup.placelessSetUp()
    setup.setUpTraversal()


def doctest_PersonGroupDataExporterPlugin():
    """Tests for PersonGroupDataExporterPlugin.

    This plugin renders a list of group ids person passed to it as a
    parameter belongs to:

        >>> from schooltool.basicperson.browser.xml import PersonGroupDataExporterPlugin
        >>> plugin = PersonGroupDataExporterPlugin("Context", TestRequest())

        >>> class GroupStub(object):
        ...     def __init__(self, name):
        ...         self.__name__ = name

        >>> from schooltool.course.interfaces import ISection
        >>> class SectionStub(object):
        ...     implements(ISection)
        ...     def __init__(self, name):
        ...         self.__name__ = name

        >>> class PersonStub(object):
        ...     groups = [GroupStub("managers"),
        ...               GroupStub("newbs"),
        ...               SectionStub("a42-b")]

    The person is a member of 2 groups and one section, though
    sections are not included in the list so we only see "mangers" and
    "newbs" in there:

        >>> person = PersonStub()
        >>> print plugin.render(person)
        <groups>
          <group id="managers" />
          <group id="newbs" />
        </groups>

    """


def doctest_GroupDataExporterPlugin():
    """Tests for GroupDataExporterPlugin.

    This plugin lists all the groups that persons in the person list
    passed to the render method belong to:

        >>> from schooltool.basicperson.browser.xml import GroupDataExporterPlugin
        >>> from schooltool.basicperson.browser.interfaces import IExtraDataExporterPlugin
        >>> plugin = GroupDataExporterPlugin("Context", TestRequest())
        >>> verifyObject(IExtraDataExporterPlugin, plugin)
        True

    We will need some groups and some sections:

        >>> from schooltool.course.interfaces import ISection
        >>> class GroupStub(object):
        ...     def __init__(self, name):
        ...         self.title = name
        ...         self.__name__ = name
        ...         self.description = "A group with title '%s'." % name

        >>> class SectionStub(object):
        ...     implements(ISection)
        ...     def __init__(self, name):
        ...         self.__name__ = name

        >>> class PersonStub(object):
        ...     groups = []

        >>> managers = GroupStub("managers")
        >>> newbs = GroupStub("newbs")
        >>> bozos = GroupStub("bozos")

    We add persons to those groups:

        >>> person1 = PersonStub()
        >>> person1.groups = [managers,
        ...                   newbs,
        ...                   SectionStub("a42-b")]

        >>> person2 = PersonStub()
        >>> person2.groups = [managers,
        ...                   bozos]

    And render the view:

        >>> print plugin.render([person1, person2])
        <groups>
          <group>
            <id>bozos</id>
            <title>bozos</title>
            <description>A group with title 'bozos'.</description>
          </group>
          <group>
            <id>managers</id>
            <title>managers</title>
            <description>A group with title 'managers'.</description>
          </group>
          <group>
            <id>newbs</id>
            <title>newbs</title>
            <description>A group with title 'newbs'.</description>
          </group>
        </groups>

    As you can see managers group was rendered only once, and all the
    sections were not shown in the list.

    """


def doctest_PersonContainerXMLExportView():
    """Tests for PersonContainerXMLExportView.

    XML export view supports plugins so you could extend the export
    functionality without changing schooltool code:

        >>> from schooltool.basicperson.browser.xml import PersonContainerXMLExportView
        >>> view = PersonContainerXMLExportView("context", TestRequest())

    If there are not plugins registered, both plugin lookup methods
    return empty lists:

        >>> view.extra_data_exporters()
        []

        >>> view.person_data_exporters()
        []

    But you can register some plugins:

        >>> from schooltool.basicperson.browser.interfaces import IPersonDataExporterPlugin
        >>> def PluginFactory(name):
        ...     class PluginStub(BrowserView):
        ...         __name__ = "<Plugin %s>" % name
        ...     return PluginStub

    And they will be listed in alphabetical order:

        >>> provideAdapter(PluginFactory("1"), [Interface, IBrowserRequest],
        ...                IPersonDataExporterPlugin, name="plugin1")
        >>> provideAdapter(PluginFactory("2"), [Interface, IBrowserRequest],
        ...                IPersonDataExporterPlugin, name="plugin2")

        >>> [plugin.__name__ for plugin in view.person_data_exporters()]
        ['<Plugin 1>', '<Plugin 2>']

    Same thing works for IExtraDataExporterPlugin of plugins as well:

        >>> from schooltool.basicperson.browser.interfaces import IExtraDataExporterPlugin
        >>> provideAdapter(PluginFactory("3"), [Interface, IBrowserRequest],
        ...                IExtraDataExporterPlugin, name="plugin3")
        >>> provideAdapter(PluginFactory("4"), [Interface, IBrowserRequest],
        ...                IExtraDataExporterPlugin, name="plugin4")

        >>> [plugin.__name__ for plugin in view.extra_data_exporters()]
        ['<Plugin 3>', '<Plugin 4>']

    """


def tearDown(test):
    setup.placelessTearDown()


def test_suite():
    optionflags = doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS
    return doctest.DocTestSuite(optionflags=optionflags,
                                setUp=setUp, tearDown=tearDown)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
