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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Timetabling app integration.
"""

from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.interface import implements, directlyProvides
from zope.intid.interfaces import IIntIds
from zope.component import adapts, getUtility, getMultiAdapter
from zope.traversing.browser.interfaces import IAbsoluteURL
from zope.publisher.browser import BrowserView
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.schema.vocabulary import getVocabularyRegistry
from zope.traversing.browser.absoluteurl import absoluteURL
from zc.table.interfaces import ISortableColumn

import schooltool.skin.flourish.page
from schooltool.app.browser.app import ActiveSchoolYearContentMixin
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.utils import TitledContainerItemVocabulary
from schooltool.common.inlinept import InlineViewPageTemplate
from schooltool.schoolyear.interfaces import ISchoolYear
from schooltool.skin.containers import ContainerView
from schooltool.skin import flourish
from schooltool.table import table
from schooltool.term.interfaces import ITerm
from schooltool.timetable.interfaces import IHaveSchedule
from schooltool.timetable.interfaces import IHaveTimetables
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


class TimetableContainerTableFormatter(table.SchoolToolTableFormatter):

    def columns(self):
        title = table.LocaleAwareGetterColumn(
            name='title',
            title=_(u"Title"),
            getter=lambda i, f: i.title,
            subsort=True)
        starts = table.GetterColumn(
            name='starts',
            title=_(u"Starts"),
            getter=lambda i, f: i.first,
            subsort=True)
        ends = table.GetterColumn(
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


class FlourishTimetableContainerView(table.TableContainerView):

    def getColumnsAfter(self):
        delete = table.ImageInputColumn(
            'delete', title=_('Delete'),
            library='schooltool.skin.flourish',
            image='remove-icon.png',
            id_getter=table.simple_form_key)
        return [delete]

    def update(self):
        super(FlourishTimetableContainerView, self).update()

        # XXX: deletion without confirmation is quite dangerous
        delete = [
            key for key, item in self.container.items()
            if "delete.%s" % table.simple_form_key(item) in self.request]
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


class SchoolTimetablesTertiaryNavigation(flourish.page.Content,
                                         flourish.page.TertiaryNavigationManager,
                                         ActiveSchoolYearContentMixin):

    template = InlineViewPageTemplate("""
        <ul tal:attributes="class view/list_class">
          <li tal:repeat="item view/items"
              tal:attributes="class item/class">
              <a tal:attributes="href item/url"
                 tal:content="item/schoolyear/@@title" />
          </li>
        </ul>
    """)

    @property
    def items(self):
        result = []
        active = self.schoolyear
        schoolyears = active.__parent__ if active is not None else {}
        for schoolyear in schoolyears.values():
            url = '%s/%s?schoolyear_id=%s' % (
                absoluteURL(self.context, self.request),
                'timetables',
                schoolyear.__name__)
            result.append({
                    'class': schoolyear.first == active.first and 'active' or None,
                    'url': url,
                    'schoolyear': schoolyear,
                    })
        return result


class FlourishTimetablesView(table.TableContainerView,
                             ActiveSchoolYearContentMixin):

    content_template = ViewPageTemplateFile('templates/f_timetables.pt')

    @property
    def title(self):
        schoolyear = self.schoolyear
        return _('Timetables for ${schoolyear}',
                 mapping={'schoolyear': schoolyear.title})

    @property
    def container(self):
        return ITimetableContainer(self.schoolyear)


class TimetableAddLinks(flourish.page.RefineLinksViewlet):
    """Manager for Add links in FlourishTimetablesView"""


class TimetablesLinkViewlet(flourish.page.LinkViewlet,
                            ActiveSchoolYearContentMixin):

    def __init__(self, context, request, *args, **kw):
        self.request = request
        super(TimetablesLinkViewlet, self).__init__(
            self.actualContext(context), request, *args, **kw)

    def actualContext(self, context):
        return ITimetableContainer(self.schoolyear)


class TimetableDoneLink(ActiveSchoolYearContentMixin):
    template = InlineViewPageTemplate('''
        <h3 class="done-link">
          <a tal:attributes="href view/url" tal:content="view/title" />
        </h3>
    ''')

    title = _('Done')

    @property
    def schoolyear(self):
        container = ITimetableContainer(self.context)
        return ISchoolYear(IHaveTimetables(container))

    @property
    def url(self):
        app = ISchoolToolApplication(None)
        return self.url_with_schoolyear_id(app, view_name='timetables')


class FlourishManageTimetablesOverview(flourish.page.Content,
                                       ActiveSchoolYearContentMixin):

    body_template = ViewPageTemplateFile('templates/f_manage_timetables_overview.pt')

    @property
    def timetables(self):
        timetables = ITimetableContainer(self.schoolyear, None)
        if timetables is not None:
            return sorted(timetables.values(), key=lambda t:t.first,
                          reverse=True)

    def timetables_url(self):
        return self.url_with_schoolyear_id(self.context,
                                           view_name='timetables')
