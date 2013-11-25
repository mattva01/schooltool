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
Upgrade SchoolTool to generation 43.

Evolve relationships to temporal.
"""
import datetime

from zope.app.generations.utility import getRootFolder
from zope.component import getUtility
from zope.component.hooks import getSite, setSite
from zope.intid.interfaces import IIntIds

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.relationship.interfaces import IRelationshipLinks
from schooltool.relationship.relationship import share_state
from schooltool.basicperson.advisor import Advising
from schooltool.app.membership import Membership
from schooltool.app.relationships import Leadership, Instruction


def evolveRelationships(date, target, rel_type, other_role, new_type):
    links = IRelationshipLinks(target).getLinksByRole(other_role)
    for link in links:
        if link.rel_type != rel_type:
            continue
        backlink = IRelationshipLinks(link.target).find(
            link.role, target, link.my_role, link.rel_type)
        link.rel_type = backlink.rel_type = new_type
        share_state(link, backlink)
        link.state.set(date)


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


def evolve(context):
    root = getRootFolder(context)
    old_site = getSite()

    assert ISchoolToolApplication.providedBy(root)

    setSite(root)

    evolveGroupRelationships(root)
    evolveCourseRelationships(root)
    evolveResourceRelationships(root)
    evolveAdvisorRelationships(root)
    evolveSectionsRelationships(root)

    setSite(old_site)
