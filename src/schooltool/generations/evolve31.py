#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2009 Shuttleworth Foundation
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
Upgrade SchoolTool to generation 31.

Contact relationships are expected to have extra_info now.

Also, fix relationship type: change URIContact to URIContactRelationship.
"""
from zope.app.generations.utility import findObjectsProviding
from zope.app.publication.zopepublication import ZopePublication

from schooltool.basicperson.interfaces import IBasicPerson
from schooltool.relationship.interfaces import IRelationshipLinks
from schooltool.relationship.relationship import relate, unrelate
from schooltool.contact.contact import URIContactRelationship
from schooltool.contact.contact import URIContact, URIPerson
from schooltool.contact.contact import ContactPersonInfo


def evolve(context):
    root = context.connection.root().get(ZopePublication.root_name, None)

    persons = findObjectsProviding(root, IBasicPerson)
    for person in persons:
        linkset = IRelationshipLinks(person)
        links = linkset.getLinksByRole(URIContact)
        for link in links[:]:
            if link.rel_type != URIContact:
                continue
            contact = link.target

            unrelate(URIContact,
                     (person, URIPerson),
                     (contact, URIContact))

            info = ContactPersonInfo()
            info.__parent__ = person
            relate(URIContactRelationship,
                   (person, URIPerson),
                   (contact, URIContact),
                   extra_info=info)

