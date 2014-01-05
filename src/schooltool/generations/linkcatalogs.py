#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2013 Shuttleworth Foundation
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
Catalog relationship links.
Make some relationships temporal.
"""

import datetime
import transaction

from BTrees import IFBTree
from BTrees.OOBTree import OOBTree
from zope.annotation.interfaces import IAnnotations
from zope.app.generations.utility import getRootFolder
from zope.component.hooks import getSite, setSite
from zope.event import notify
from zope.intid import IIntIds
from zope.intid.interfaces import IntIdAddedEvent
from zope.lifecycleevent import ObjectAddedEvent, ObjectModifiedEvent
from zope.keyreference.interfaces import IKeyReference
from zope.component import getUtility

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.catalog import VersionedCatalog
from schooltool.app.membership import Membership
from schooltool.app.relationships import Leadership, Instruction
from schooltool.basicperson.advisor import Advising
from schooltool.contact.contact import URIContactRelationship, URIContact, URIPerson
from schooltool.relationship.relationship import getLinkCatalog
from schooltool.relationship.catalog import LinkCatalog, URICache
from schooltool.relationship.temporal import TemporalURIObject
from schooltool.relationship.interfaces import IRelationshipLinks
from schooltool.app.membership import URIMembership, URIGroup, URIMember
from schooltool.app.overlay import URICalendarSubscription
from schooltool.app.overlay import URICalendarProvider
from schooltool.app.overlay import URICalendarSubscriber
from schooltool.app.relationships import URIInstruction
from schooltool.app.relationships import URIInstructor
from schooltool.app.relationships import URISection
from schooltool.app.relationships import URICourseSections
from schooltool.app.relationships import URICourse
from schooltool.app.relationships import URISectionOfCourse
from schooltool.app.relationships import URILeadership
from schooltool.app.relationships import URILeader
from schooltool.app.relationships import URIAsset
from schooltool.basicperson.advisor import URIAdvising
from schooltool.basicperson.advisor import URIStudent
from schooltool.basicperson.advisor import URIAdvisor
from schooltool.course.booking import URISectionBooking
from schooltool.course.booking import URIResource
from schooltool.level.level import URILevelCourses
from schooltool.level.level import URILevel


PERSON_CONTACT_KEY = 'schooltool.contact.basicperson'

CONTACT_RELATIONSHIPS_MAP = {
    'parent': ('ap', 'p'),
    'step_parent': ('ap', 'sp'),
    'foster_parent': ('ap', 'fp'),
    'guardian': ('ap', 'g'),
    'sibling': ('a', 's'),
}

def addLinkCatalog(app):
    catalogs = app['schooltool.app.catalog:Catalogs']
    factory = LinkCatalog(app)
    version = factory.getVersion()
    catalog = factory.createCatalog()
    catalogs[factory.key()] = VersionedCatalog(catalog, version)
    factory.setIndexes(catalog)


def collectOIDs(connection):
    storage = connection._storage
    next_oid = None
    link_oids = []
    linkset_oids = []
    total = 0
    while True:
        oid, tid, data, next_oid = storage.record_iternext(next_oid)
        total += 1
        if data.startswith('cschooltool.relationship.relationship\nLink\n'):
            if oid not in link_oids:
                link_oids.append(oid)
        elif data.startswith('cschooltool.relationship.relationship\nLinkSet\n'):
            if oid not in linkset_oids:
                linkset_oids.append(oid)
        if next_oid is None:
            break

    return link_oids, linkset_oids


def evolveLinks(connection, oids):
    int_ids = getSite()._sm.getUtility(IIntIds)

    states = {}
    for n, oid in enumerate(oids):
        try:
            link = connection.get(oid)
        except KeyError:
            continue
        links = link.__parent__._links
        if (link.__name__ not in links or
            links[link.__name__] is not link):
            # this is a record of a replaced link, skip.
            continue
        key = IKeyReference(link)
        idmap = {
            int_ids: int_ids.register(key)}

        this = link.__parent__.__parent__
        thishash = (
            hash(IKeyReference(this)), hash(link.my_role),
            hash(IKeyReference(link.target)), hash(link.role),
            hash(link.rel_type),
            )
        backhash = (
            hash(IKeyReference(link.target)), hash(link.role),
            hash(IKeyReference(this)), hash(link.my_role),
            hash(link.rel_type),
            )

        if backhash in states:
            link.shared = states[thishash] = states[backhash]
        else:
            assert thishash not in states
            states[thishash] = link.shared = OOBTree()
            link.shared['X'] = link.__dict__.get('extra_info')
        if 'extra_info' in link.__dict__:
            del link.__dict__['extra_info']
        if isinstance(link.rel_type, TemporalURIObject):
            link.shared['tmp'] = ()

        notify(IntIdAddedEvent(link, ObjectAddedEvent(link), idmap))

        if n % 10000 == 9999:
            transaction.savepoint(optimistic=True)


def evolveLinkSets(connection, oids):
    int_ids = getSite()._sm.getUtility(IIntIds)

    for oid in oids:
        try:
            linkset = connection.get(oid)
        except KeyError:
            continue
        if getattr(linkset, '_lids', None) is None:
            linkset._lids = IFBTree.TreeSet()
        linkset._lids.clear()
        for link in linkset._links.values():
            linkset._lids.add(int_ids.getId(link))


def evolveRelationships(date, target, rel_type, other_role, new_type):
    int_ids = getUtility(IIntIds)
    links = IRelationshipLinks(target).iterLinksByRole(other_role)
    for link in links:
        link = int_ids.getObject(link.lid)
        if link.rel_type != rel_type:
            continue
        backlink = IRelationshipLinks(link.target).find(
            link.role, target, link.my_role, link.rel_type)
        link.rel_type = backlink.rel_type = new_type
        if 'tmp' not in link.shared:
            link.shared['tmp'] = ()
        link.state.set(date)
        notify(ObjectModifiedEvent(link))
        notify(ObjectModifiedEvent(backlink))


def evolveSectionsRelationships(app):
    int_ids = getUtility(IIntIds)
    containers = app['schooltool.course.section']
    for term_id, container in containers.items():
        term = int_ids.getObject(int(term_id))
        for section in container.values():
            members = section.members
            evolveRelationships(
                term.first, section, members.rel_type, members.other_role,
                Membership.rel_type)
            instructors = section.instructors
            evolveRelationships(
                term.first, section, instructors.rel_type, instructors.other_role,
                Instruction.rel_type)


def evolveGroupRelationships(app):
    int_ids = getUtility(IIntIds)
    containers = app['schooltool.group']
    for term_id, container in containers.items():
        term = int_ids.getObject(int(term_id))
        for group in container.values():
            members = group.members
            evolveRelationships(
                term.first, group, members.rel_type, members.other_role,
                Membership.rel_type)
            leaders = group.leaders
            evolveRelationships(
                term.first, group, leaders.rel_type, leaders.other_role,
                Leadership.rel_type)


def evolveCourseRelationships(app):
    int_ids = getUtility(IIntIds)
    containers = app['schooltool.course.course']
    for year_id, container in containers.items():
        year = int_ids.getObject(int(year_id))
        for course in container.values():
            leaders = course.leaders
            evolveRelationships(
                year.first, course, leaders.rel_type, leaders.other_role,
                Leadership.rel_type)


def evolveResourceRelationships(app):
    if app['schooltool.schoolyear']:
        date = min([year.first for year in app['schooltool.schoolyear'].values()])
    else:
        date = datetime.datetime.today().date()

    container = app['resources']
    for name, resource in container.items():
        leaders = resource.leaders
        evolveRelationships(
            date, resource, leaders.rel_type, leaders.other_role,
                Leadership.rel_type)


def evolveAdvisorRelationships(app):
    if app['schooltool.schoolyear']:
        date = min([year.first for year in app['schooltool.schoolyear'].values()])
    else:
        date = datetime.datetime.today().date()
    for person in app['persons'].values():
        advisors = person.advisors
        evolveRelationships(
            date, person, advisors.rel_type, advisors.other_role,
            Advising.rel_type)


def evolveContactRelationships(app):
    if app['schooltool.schoolyear']:
        date = min([year.first for year in app['schooltool.schoolyear'].values()])
    else:
        date = datetime.datetime.today().date()

    contacts = app['schooltool.contact'].values()
    for contact in contacts:
        evolveRelationships(
            date, contact, URIContactRelationship, URIPerson,
            URIContactRelationship)
        # Also evolve pre gen-31 relationships
        evolveRelationships(
            date, contact, URIContact, URIPerson,
            URIContactRelationship)

    persons = app['persons'].values()
    for person in persons:
        annotations = IAnnotations(person)
        bound = annotations.get(PERSON_CONTACT_KEY, None)
        if bound is None:
            continue
        evolveRelationships(
            date, bound, URIContactRelationship, URIPerson,
            URIContactRelationship)
        # Also evolve pre gen-31 relationships
        evolveRelationships(
            date, bound, URIContact, URIPerson,
            URIContactRelationship)

    catalog = getLinkCatalog()
    int_ids = getUtility(IIntIds)

    for n, iid in enumerate(catalog.extent):
        if (n+1) % 10000 == 0:
            transaction.savepoint(optimistic=True)

        link = int_ids.getObject(iid)
        if link.rel_type != URIContactRelationship:
            continue
        shared = link.shared_state
        extra_info = shared['X']
        if extra_info is None:
            continue
        meaning, code = CONTACT_RELATIONSHIPS_MAP.get(
            extra_info.relationship, ('a', 'a'))
        link.state.set(date, meaning=meaning, code=code)
        shared['X'] = None


def requireURICache(app):
    if 'schooltool.relationship.uri' not in app:
        cache = app['schooltool.relationship.uri'] = URICache()
        standard_uris = [
            URIMembership, URIGroup, URIMember, URICalendarSubscription,
            URICalendarProvider, URICalendarSubscriber, URIInstruction,
            URIInstructor, URISection, URICourseSections, URICourse,
            URISectionOfCourse, URILeadership, URILeader, URIAsset,
            URIAdvising, URIStudent, URIAdvisor, URIContactRelationship,
            URIContact, URIPerson, URISectionBooking, URISection,
            URIResource, URILevelCourses, URICourse, URILevel]
        for uri in standard_uris:
            cache.cache(uri)


def evolve(context):
    root = getRootFolder(context)
    old_site = getSite()

    assert ISchoolToolApplication.providedBy(root)
    setSite(root)

    requireURICache(root)

    connection = context.connection

    link_oids, linkset_oids = collectOIDs(connection)

    evolveLinks(connection, link_oids)
    transaction.savepoint(optimistic=True)

    evolveLinkSets(connection, linkset_oids)
    transaction.savepoint(optimistic=True)

    addLinkCatalog(root)
    transaction.savepoint(optimistic=True)

    evolveGroupRelationships(root)
    evolveCourseRelationships(root)
    evolveResourceRelationships(root)
    evolveAdvisorRelationships(root)
    evolveSectionsRelationships(root)

    transaction.savepoint(optimistic=True)

    evolveContactRelationships(root)

    setSite(old_site)


def ensureEvolved(context):
    root = getRootFolder(context)
    assert ISchoolToolApplication.providedBy(root)
    catalogs = root['schooltool.app.catalog:Catalogs']
    if LinkCatalog.key() in catalogs:
        return
    evolve(context)
    transaction.commit()
