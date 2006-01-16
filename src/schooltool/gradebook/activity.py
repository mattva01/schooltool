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
"""Activity implementation

$Id$
"""
__docformat__ = 'reStructuredText'

import datetime
import zope.interface
from zope.app import annotation
from schooltool.requirement import requirement
from schooltool.traverser import traverser

from schooltool.gradebook import interfaces

ACTIVITIES_KEY = 'schooltool.gradebook.activities'

class Activities(requirement.Requirement):
    zope.interface.implements(interfaces.IActivities)


class Activity(requirement.Requirement):
    zope.interface.implements(interfaces.IActivity)

    def __init__(self, title, category, scoresystem,
                 description=None, date=None):
        super(Activity, self).__init__(title)
        self.description = description
        self.category = category
        self.scoresystem = scoresystem
        if not date:
            date = datetime.date.today()
        self.date = date

    def __repr__(self):
        return '<%s %r>' %(self.__class__.__name__, self.title)

def getCourseActivities(context):
    '''IAttributeAnnotatable object to IActivities adapter.'''
    annotations = annotation.interfaces.IAnnotations(context)
    try:
        return annotations[ACTIVITIES_KEY]
    except KeyError:
        activities = Activities(context.title)
        annotations[ACTIVITIES_KEY] = activities
        zope.app.container.contained.contained(
            activities, context, 'activities')
        return activities

# Convention to make adapter introspectable
getCourseActivities.factory = Activities


def getSectionActivities(context):
    '''IAttributeAnnotatable object to IActivities adapter.'''
    annotations = annotation.interfaces.IAnnotations(context)
    try:
        return annotations[ACTIVITIES_KEY]
    except KeyError:
        activities = Activities(context.title)
        # Make sure that the sections activities include all the activities of
        # the courses as well
        for course in context.courses:
            activities.addBase(getCourseActivities(course))
        annotations[ACTIVITIES_KEY] = activities
        zope.app.container.contained.contained(
            activities, context, 'activities')
        return activities

# Convention to make adapter introspectable
getSectionActivities.factory = Activities

# HTTP pluggable traverser plugin
ActivitiesTraverserPlugin = traverser.AdapterTraverserPlugin(
    'activities', interfaces.IActivities)
