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
Base classes for report reference and request adapters

"""

from zope.component import adapts, adapter
from zope.component import getUtility
from zope.interface import implements, implementer
from zope.traversing.browser import absoluteURL

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.basicperson.interfaces import IBasicPerson
from schooltool.common import SchoolToolMessage as _
from schooltool.course.interfaces import ISection, ISectionContainer
from schooltool.group.interfaces import IGroup, IGroupContainer
from schooltool.person.interfaces import IPersonContainer
from schooltool.report.interfaces import IReportRequest, IReportReference
from schooltool.schoolyear.interfaces import ISchoolYear
from schooltool.skin.skin import ISchoolToolLayer
from schooltool.term.interfaces import ITerm, IDateManager


##################     Report Reference   ####################
class BaseReportReference(object):
    adapts(ISchoolToolApplication, ISchoolToolLayer)
    implements(IReportReference)

    title = None
    description = None
    category = None
    url = None

    def __init__(self, context, request):
        self.context = context
        self.request = request


class CurrentTermBasedReportReference(BaseReportReference):
    @property
    def url(self):
        current_term = getUtility(IDateManager).current_term
        if current_term is None:
            return ''
        return self.fromTerm(current_term)


class StudentReportReference(BaseReportReference):
    category = _('Student')

    @property
    def url(self):
        return absoluteURL(self.context['persons'], self.request)


class GroupReportReference(CurrentTermBasedReportReference):
    category = _('Group')

    def fromTerm(self, term):
        return absoluteURL(IGroupContainer(ISchoolYear(term)), self.request)


class SchoolYearReportReference(CurrentTermBasedReportReference):
    category = _('School Year')

    def fromTerm(self, term):
        return absoluteURL(ISchoolYear(term), self.request)


class TermReportReference(CurrentTermBasedReportReference):
    category = _('Term')

    def fromTerm(self, term):
        return absoluteURL(term, self.request)


class SectionReportReference(CurrentTermBasedReportReference):
    category = _('Section')

    def fromTerm(self, term):
        return absoluteURL(ISectionContainer(term), self.request)


##################     Report Request   ####################
class BaseReportRequest(object):
    implements(IReportRequest)

    title = None

    def __init__(self, context, request):
        self.context = context
        self.request = request

    @property
    def url(self):
        return absoluteURL(self.context, self.request) + self.extra


class StudentReportRequest(BaseReportRequest):
    adapts(IBasicPerson, ISchoolToolLayer)


class GroupReportRequest(BaseReportRequest):
    adapts(IGroup, ISchoolToolLayer)


class SchoolYearReportRequest(BaseReportRequest):
    adapts(ISchoolYear, ISchoolToolLayer)


class TermReportRequest(BaseReportRequest):
    adapts(ITerm, ISchoolToolLayer)


class SectionReportRequest(BaseReportRequest):
    adapts(ISection, ISchoolToolLayer)

