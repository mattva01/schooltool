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
"""
course browser views.

$Id$
"""
from zope.interface import implements
from zope.security.proxy import removeSecurityProxy
from zope.app.intid.interfaces import IIntIds
from zope.app.form.browser.add import AddView
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.publisher.browser import BrowserView
from zope.component import adapts
from zope.component import getUtility
from zope.component import getMultiAdapter
from zope.app.container.contained import NameChooser
from zope.app.container.interfaces import INameChooser
from zc.table import table
from zope.traversing.browser.interfaces import IAbsoluteURL
from zope.traversing.browser.absoluteurl import absoluteURL

from schooltool.person.interfaces import IPerson
from schooltool.group.interfaces import IGroupContainer
from schooltool.group.interfaces import IGroup
from schooltool.term.interfaces import ITerm
from schooltool.timetable.interfaces import ITimetables
from schooltool.schoolyear.interfaces import ISchoolYear
from schooltool.skin.containers import ContainerView
from schooltool.app.browser.app import BaseEditView

from schooltool.common import SchoolToolMessage as _
from schooltool.course.interfaces import ICourseContainer
from schooltool.course.interfaces import ISection, ISectionContainer
from schooltool.course.section import Section
from schooltool.app.browser.app import RelationshipViewBase
from schooltool.timetable.browser import TimetableConflictMixin
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.table.interfaces import ITableFormatter


class SectionContainerAbsoluteURLAdapter(BrowserView):

    adapts(ISectionContainer, IBrowserRequest)
    implements(IAbsoluteURL)

    def __str__(self):
        container_id = int(self.context.__name__)
        int_ids = getUtility(IIntIds)
        container = int_ids.getObject(container_id)
        url = str(getMultiAdapter((container, self.request), name='absolute_url'))
        return url + '/sections'

    __call__ = __str__


class SectionContainerView(ContainerView):
    """A Course Container view."""

    __used_for__ = ISectionContainer

    @property
    def term(self):
        return ITerm(self.context)

    @property
    def school_year(self):
        return ISchoolYear(self.context)

    # XXX: very hacky, but necessary for now. :-(
    def getTimetables(self, obj):
        return []
        timetables = sorted(ITimetables(obj).timetables.items())
        return [timetable
                for key, timetable in timetables]


class SectionView(BrowserView):
    """A view for courses providing a list of sections."""

    __used_for__ = ISection

    @property
    def term(self):
        return ITerm(self.context)

    @property
    def school_year(self):
        return ISchoolYear(self.context)

    def renderPersonTable(self):
        persons = ISchoolToolApplication(None)['persons']
        formatter = getMultiAdapter((persons, self.request), ITableFormatter)
        formatter.setUp(table_formatter=table.StandaloneFullFormatter,
                        items=self.getPersons(),
                        batch_size=0)
        return formatter.render()

    def getPersons(self):
        return map(removeSecurityProxy,
                   filter(IPerson.providedBy, self.context.members))

    def getGroups(self):
        return filter(IGroup.providedBy, self.context.members)


class SectionNameChooser(NameChooser):

    implements(INameChooser)

    def chooseName(self, name, obj):
        """See INameChooser."""

        i = 1
        n = "1"
        while n in self.context:
            i += 1
            n = unicode(i)
        # Make sure the name is valid
        self.checkName(n, obj)
        return n


class SectionAddView(AddView):
    """A view for adding Sections."""

    def getCourseFromId(self, cid):
        try:
            return ICourseContainer(self.context.context)[cid]
        except KeyError:
            self.error = _("No such course.")

    def __init__(self, context, request):
        super(AddView, self).__init__(context, request)

        try:
            course_id = request['field.course_id']
        except KeyError:
            self.error = _("Need a course ID.")
            return

        self.course = self.getCourseFromId(course_id)

    def __call__(self):
        section = Section()
        self.context.add(section)
        self.course.sections.add(section)
        section.title = "%s (%s)" % (self.course.title, section.__name__)
        self.request.response.redirect(absoluteURL(section, self.request))


class SectionEditView(BaseEditView):
    """View for editing Sections."""

    __used_for__ = ISection


class ConflictDisplayMixin(TimetableConflictMixin):
    """A mixin for use in views that display event conflicts."""

    def update(self):
        """Set self.busy_periods."""
        ttschema = self.getSchema()
        term = self.getTerm()
        if ttschema and term:
            section_map = self.sectionMap(term, ttschema)
            self.busy_periods = [(key, sections)
                                 for key, sections in section_map.items()
                                 if self.context in sections]
        else:
            self.busy_periods = []


class RelationshipEditConfView(RelationshipViewBase, ConflictDisplayMixin):
    """A relationship editing view that displays conflicts."""

    def update(self):
        RelationshipViewBase.update(self)
        ConflictDisplayMixin.update(self)


class SectionInstructorView(RelationshipEditConfView, ConflictDisplayMixin):
    """View for adding instructors to a Section."""

    __used_for__ = ISection

    title = _("Instructors")
    current_title = _("Current Instructors")
    available_title = _("Available Instructors")

    def getCollection(self):
        return self.context.instructors

    def getAvailableItemsContainer(self):
        return ISchoolToolApplication(None)['persons']


class SectionLearnerView(RelationshipEditConfView):
    """View for adding learners to a Section.  """

    __used_for__ = ISection

    title = _("Students")
    current_title = _("Current Students")
    available_title = _("Available Students")

    def getCollection(self):
        return self.context.members

    def getSelectedItems(self):
        """Return a list of selected members."""
        return filter(IPerson.providedBy, self.getCollection())

    def getAvailableItemsContainer(self):
        return ISchoolToolApplication(None)['persons']


class SectionLearnerGroupView(RelationshipEditConfView):
    """View for adding learners to a Section."""

    __used_for__ = ISection

    title = _("Groups")
    current_title = _("Current Groups")
    available_title = _("Available Groups")

    def getCollection(self):
        return self.context.members

    def getSelectedItems(self):
        """Return a list of selected members."""
        return filter(IGroup.providedBy, self.getCollection())

    def getAvailableItemsContainer(self):
        return IGroupContainer(self.context)
