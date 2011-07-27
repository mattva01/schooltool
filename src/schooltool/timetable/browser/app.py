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

from zope.interface import implements, directlyProvides
from zope.intid.interfaces import IIntIds
from zope.component import adapts, queryAdapter, getUtility, getMultiAdapter
from zope.traversing.browser.interfaces import IAbsoluteURL
from zope.publisher.browser import BrowserView
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.schema.vocabulary import getVocabularyRegistry
from zope.traversing.browser.absoluteurl import absoluteURL
from zc.table.interfaces import ISortableColumn

import schooltool.skin.flourish.page
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.utils import TitledContainerItemVocabulary
from schooltool.schoolyear.interfaces import ISchoolYear
from schooltool.skin.containers import ContainerView
from schooltool.skin import flourish
from schooltool.table.table import SchoolToolTableFormatter
from schooltool.table.table import GetterColumn, LocaleAwareGetterColumn
from schooltool.table.table import ImageInputColumn
from schooltool.table.table import simple_form_key
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


class TimetableContainerTableFormatter(SchoolToolTableFormatter):

    def columns(self):
        title = LocaleAwareGetterColumn(
            name='title',
            title=_(u"Title"),
            getter=lambda i, f: i.title,
            subsort=True)
        starts = GetterColumn(
            name='starts',
            title=_(u"Starts"),
            getter=lambda i, f: i.first,
            subsort=True)
        ends = GetterColumn(
            name='ends',
            title=_(u"Ends"),
            getter=lambda i, f: i.last,
            subsort=True)
        directlyProvides(title, ISortableColumn)
        directlyProvides(starts, ISortableColumn)
        directlyProvides(ends, ISortableColumn)
        return [title, starts, ends]

    def sortOn(self):
        return (('title', False), ("starts", False), ("ends", False),)


class FlourishTimetableContainerView(flourish.containers.TableContainerView):

    def getColumnsAfter(self):
        delete = ImageInputColumn(
            'delete', title=_('Delete'),
            library='schooltool.skin.flourish',
            image='remove-icon.png',
            id_getter=simple_form_key)
        return [delete]

    def update(self):
        super(FlourishTimetableContainerView, self).update()

        # XXX: deletion without confirmation is quite dangerous
        delete = [key for key, item in self.container.items()
                  if "delete.%s" % simple_form_key(item) in self.request]
        for key in delete:
            del self.container[key]
        if delete:
            self.request.response.redirect(
                absoluteURL(self.context, self.request))


class FlourishTimetableContainerLinks(flourish.page.RefineLinksViewlet):
    """demographics fields add links viewlet."""


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
