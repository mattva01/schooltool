#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2011 Shuttleworth Foundation
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
Timetabling app integration.
"""

from zope.interface import implements
from zope.intid.interfaces import IIntIds
from zope.component import adapts, getMultiAdapter, getUtility
from zope.traversing.browser.interfaces import IAbsoluteURL
from zope.publisher.browser import BrowserView
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.schema.vocabulary import getVocabularyRegistry

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.utils import TitledContainerItemVocabulary
from schooltool.schoolyear.interfaces import ISchoolYear
from schooltool.skin.containers import ContainerView
from schooltool.term.interfaces import ITerm
from schooltool.timetable.interfaces import IHaveSchedule
from schooltool.timetable.interfaces import IScheduleContainer
from schooltool.timetable.interfaces import ITimetableContainer

from schooltool.common import SchoolToolMessage as _


class ScheduleContainerAbsoluteURLAdapter(BrowserView):

    adapts(IScheduleContainer, IBrowserRequest)
    implements(IAbsoluteURL)

    traversal_name = 'schedule'

    def __str__(self):
        container_id = int(self.context.__name__)
        int_ids = getUtility(IIntIds)
        container = int_ids.getObject(container_id)
        url = str(getMultiAdapter((container, self.request), name='absolute_url'))
        return '%s/%s' % (url, self.traversal_name)

    __call__ = __str__


class TimetableContainerAbsoluteURLAdapter(ScheduleContainerAbsoluteURLAdapter):
    adapts(ITimetableContainer, IBrowserRequest)

    traversal_name = 'timetables'


# XXX: the view is not working yet, default selection broken
# XXX: timetable deletion view not implemented
class TimetableContainerView(ContainerView):
    """TimetableContainer view."""

    index_title = _("School Timetables")

    def update(self):
        if 'UPDATE_SUBMIT' in self.request:
            default = self.context.get(self.request['ttschema'])
            self.context.default = default
        return ''


def getActivityVocabulary(object=None):
    if object is None:
        object = ISchoolToolApplication(None)
    vr = getVocabularyRegistry()
    vocabulary = vr.get(object, 'schooltool.timetable.activityvocbulary')
    return vocabulary


class TimetableVocabulary(TitledContainerItemVocabulary):
    @property
    def container(self):
        owner = IHaveSchedule(self.context)
        return ITimetableContainer(ISchoolYear(ITerm(owner)), {})


def timetableVocabularyFactory():
    return TimetableVocabulary
