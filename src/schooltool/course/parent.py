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
Parent access.
"""
from zope.component import adapts

from schooltool.securitypolicy.crowds import Crowd, AggregateCrowd
from schooltool.securitypolicy.crowds import ClerksCrowd, AdministratorsCrowd
from schooltool.course import interfaces
from schooltool.course.section import LearnersCrowd, InstructorsCrowd
from schooltool.course.section import SectionCalendarSettingCrowd
from schooltool.contact.contact import ParentCrowd, ParentOfCrowd

from schooltool.common import SchoolToolMessage as _


class ParentsOfLearnersCrowd(Crowd):
    """Crowd of learners of a section.

    At the moment only direct members of a section are considered as
    learners.
    """
    adapts(interfaces.ISection)

    title = _(u'Learners')
    description = _(u'Students of the section.')

    def contains(self, principal):
        if not ParentCrowd(self.context).contains(principal):
            return False
        for member in self.context.members:
            if ParentOfCrowd(member).contains(principal):
                return True
        return False


class SectionCalendarViewers(AggregateCrowd):
    """Crowd of those who can see the section calendar."""
    adapts(interfaces.ISection)

    def crowdFactories(self):
        return [ClerksCrowd, AdministratorsCrowd,
                InstructorsCrowd, LearnersCrowd, SectionCalendarSettingCrowd,
                ParentsOfLearnersCrowd]
