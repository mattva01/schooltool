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
Basic person import export views.

$Id$
"""
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.component import getAdapters
from zope.interface import implements
from zope.publisher.browser import BrowserView

from schooltool.course.interfaces import ISection
from schooltool.basicperson.browser.interfaces import IPersonDataExporterPlugin
from schooltool.basicperson.browser.interfaces import IExtraDataExporterPlugin


class PersonGroupDataExporterPlugin(BrowserView):
    """Plugin that list all the ids of groups this person belongs to."""
    implements(IPersonDataExporterPlugin)

    template = ViewPageTemplateFile("templates/person_groups.pt")

    def __init__(self, context, request):
        self.context, self.request = context, request

    def render(self, person):
        self.groups = set()
        for group in person.groups:
            if not ISection.providedBy(group):
                self.groups.add(group)
        self.groups = sorted(list(self.groups),
                             key=lambda g: g.__name__)
        return self.template()


class GroupDataExporterPlugin(BrowserView):
    """Plugin that exports all the groups persons belong to."""
    implements(IExtraDataExporterPlugin)

    template = ViewPageTemplateFile("templates/groups.pt")

    def __init__(self, context, request):
        self.context, self.request = context, request

    def render(self, persons):
        self.groups = set()
        for person in persons:
            for group in person.groups:
                if not ISection.providedBy(group):
                    self.groups.add(group)
        self.groups = sorted(list(self.groups),
                             key=lambda g: g.__name__)
        return self.template()


class PersonContainerXMLExportView(BrowserView):

    template =  ViewPageTemplateFile("templates/persons_xml_export.pt")

    def persons(self):
        persons = []
        for person in self.context.values():
            yield person

    def person_data_exporters(self):
        plugins = getAdapters(
            (self.context, self.request),
            IPersonDataExporterPlugin)
        return [plugin for id, plugin in sorted(plugins)]

    def extra_data_exporters(self):
        plugins = getAdapters(
            (self.context, self.request),
            IExtraDataExporterPlugin)
        return [plugin for id, plugin in sorted(plugins)]

    def __call__(self):
        return self.template()


class PersonXMLExportView(PersonContainerXMLExportView):

    def persons(self):
        return [self.context]
