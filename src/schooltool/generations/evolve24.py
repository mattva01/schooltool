#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2006 Shuttleworth Foundation
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
Upgrade SchoolTool to generation 24.

$Id$
"""
from BTrees.OOBTree import OOBTree

from zope.app.publication.zopepublication import ZopePublication
from zope.app.generations.utility import findObjectsProviding

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.resource.resource import Location
from schooltool.resource.interfaces import IResource
from schooltool.relationship.relationship import relate
from schooltool.relationship.relationship import unrelate
from schooltool.relationship.interfaces import IRelationshipLinks
from schooltool.app.interfaces import ISchoolToolCalendar


def evolve(context):
    root = context.connection.root()[ZopePublication.root_name]
    for app in findObjectsProviding(root, ISchoolToolApplication):
        resources = app['resources']
        for resource_id, resource in resources.items():
            ann = resource.__annotations__

            if IResource.providedBy(resource) and resource.isLocation:
                # title, description
                new_resource = Location(resource.title, resource.description)

                links = IRelationshipLinks(resource)
                link_tuples = []
                for link in list(links):
                    uri, a, rel_a, b, rel_b = (link.rel_type,
                                               link.target,
                                               link.role,
                                               resource,
                                               link.my_role)
                    unrelate(uri, (a, rel_a), (b, rel_b))
                    link_tuples.append((uri, (a, rel_a), (b, rel_b)))

                # no relationships should be left in there
                assert len(list(IRelationshipLinks(resource))) == 0

                new_resource.__annotations__ = OOBTree()
                for key, annotation in list(resource.__annotations__.items()):
                    new_resource.__annotations__[key] = annotation
                    # we don't want annotations affected by actions
                    # performed with the old resource object
                    del resource.__annotations__[key]
                    if (hasattr(annotation, '__parent__') and
                        annotation.__parent__ is resource):
                        annotation.__parent__ = new_resource

                calendar = new_resource.__annotations__.get(
                    'schooltool.app.calendar.Calendar', None)
                if calendar:
                    for ev in calendar:
                        new_resource_list = []
                        for res in ev._resources:
                            if res.__name__ == resource_id:
                                new_resource_list.append(new_resource)
                            else:
                                new_resource_list.append(res)
                        ev._resources = tuple(new_resource_list)

                del resources[resource_id]
                resources[resource_id] = new_resource

                for link in link_tuples:
                    relate(*link)
