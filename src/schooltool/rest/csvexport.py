#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003 Shuttleworth Foundation
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
CSV export of organisational structure.

$Id$
"""

import csv
import zipfile
from cStringIO import StringIO
from schooltool.rest import View
from schooltool.uris import URIMember, URIGroup, URITaught
from schooltool.component import getRelatedObjects
from schooltool.component import FacetManager
from schooltool.component import iterFacetFactories
from schooltool.rest.auth import PublicAccess

__metaclass__ = type


class CSVExporter(View):
    """CSV export view on IApplication.

    GET returns a zip file with four CSV files inside:
      groups.csv
      pupils.csv
      teachers.csv
      resources.csv

    See the docstring of schooltool.client.csvclient for information about the
    structure of those files.

    Note that currently the files are stored inside the zip archive
    uncompressed.  To enable compression add a compression=zipfile.ZIP_STORED
    argument to ZipFile in do_GET.

    XXX Group or facet factory names that contain spaces will prevent the
        generated CSV files from being reimported.
    """

    authorization = PublicAccess

    def do_GET(self, request):
        request.setHeader('Content-Type', 'application/x-zip')
        stm = StringIO()
        zf = zipfile.ZipFile(stm, "w")
        for filename, exporter in [('groups.csv', self.exportGroups),
                                   ('pupils.csv', self.exportPupils),
                                   ('teachers.csv', self.exportTeachers),
                                   ('resources.csv', self.exportResources)]:
            zf.writestr(filename, as_csv(exporter()))
        zf.close()
        return stm.getvalue()

    def exportGroups(self):
        """Return an iterator over tuples describing groups."""
        facet_factory_names_for = FactoryNameHack().factory_names
        groups = self.context['groups']
        for group in groups.itervalues():
            if group.__name__ in ('root', 'teachers', 'pupils'):
                continue
            parent_groups = getRelatedObjects(group, URIGroup)
            group_names = " ".join([g.__name__ for g in parent_groups])
            facet_names = " ".join(facet_factory_names_for(group))
            yield group.__name__, group.title, group_names, facet_names

    def exportPupils(self):
        """Return an iterator over tuples describing pupils."""
        pupils = self.context['groups']['pupils']
        for pupil in getRelatedObjects(pupils, URIMember):
            groups = getRelatedObjects(pupil, URIGroup)
            group_names = " ".join([g.__name__ for g in groups
                                    if g is not pupils])
            person_info = FacetManager(pupil).facetByName('person_info')
            dob = person_info.date_of_birth.strftime('%Y-%m-%d')
            comment = person_info.comment
            yield pupil.title, group_names, dob, comment

    def exportTeachers(self):
        """Return an iterator over tuples describing teachers."""
        teachers = self.context['groups']['teachers']
        for teacher in getRelatedObjects(teachers, URIMember):
            groups = getRelatedObjects(teacher, URITaught)
            group_names = " ".join([g.__name__ for g in groups])
            person_info = FacetManager(teacher).facetByName('person_info')
            dob = person_info.date_of_birth.strftime('%Y-%m-%d')
            comment = person_info.comment
            yield teacher.title, group_names, dob, comment

    def exportResources(self):
        """Return an iterator over tuples describing resources."""
        for resource in self.context['resources'].itervalues():
            yield resource.title,


class FactoryNameHack:
    """Heuristic for determining facet factory names.

    The problem is as follows: given an object determine what facet factories
    can be used to create all the facets that object has.

    XXX This is a bit of a hack.  There is no clear way to determine what
        facet factories were used to create facets on a given group.  We
        cheat by assuming that facets were created by a FacetFactory whose
        'factory' argument matches the __class__ of a facet.
    """

    def __init__(self):
        factory_map = {}
        for factory in iterFacetFactories():
            if hasattr(factory, 'factory'):
                factory_map[factory.factory] = factory.name
        self.factory_map = factory_map

    def factory_names(self, obj):
        """Return an iterator of facet factory names for obj's facets.

        Owned facets are ignored as they are never created manually.
        """
        for facet in FacetManager(obj).iterFacets():
            if facet.owner is not None:
                continue
            factory_name = self.factory_map.get(facet.__class__)
            if factory_name is not None:
                yield factory_name


def as_csv(rows):
    """Format a sequence of tuples as CSV data."""
    stm = StringIO()
    writer = csv.writer(stm)
    writer.writerows(rows)
    return stm.getvalue()

