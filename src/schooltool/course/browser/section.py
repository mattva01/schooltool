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
from zope.security.proxy import removeSecurityProxy
from zope.app.form.browser.add import AddView
from zope.publisher.browser import BrowserView
from zope.component import getMultiAdapter
from zope.app.container.interfaces import INameChooser
from zc.table import table
from zope.traversing.browser.absoluteurl import absoluteURL

from schooltool.person.interfaces import IPerson
from schooltool.group.interfaces import IGroup
from schooltool.timetable.interfaces import ITimetables
from schooltool.skin.containers import ContainerView
from schooltool.app.browser.app import BaseEditView

from schooltool.common import SchoolToolMessage as _
from schooltool.common import collect
from schooltool.course.interfaces import ISection, ISectionContainer
from schooltool.relationship.relationship import getRelatedObjects
from schooltool.app.membership import URIGroup
from schooltool.app.relationships import URISection
from schooltool.course import booking
from schooltool.course.section import Section
from schooltool.app.interfaces import ISchoolToolCalendar
from schooltool.timetable.interfaces import ICompositeTimetables
from schooltool.app.browser.app import RelationshipViewBase
from schooltool.timetable.browser import TimetableConflictMixin
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.table.interfaces import ITableFormatter


def same(a, b):
    """Check if two possibly proxied objects are one and the same."""
    return removeSecurityProxy(a) is removeSecurityProxy(b)


class SectionContainerView(ContainerView):
    """A Course Container view."""

    __used_for__ = ISectionContainer

    index_title = _("Section index")

    # XXX: very hacky, but necessary for now. :-(
    def getTimetables(self, obj):
        return ITimetables(obj).timetables


class SectionView(BrowserView):
    """A view for courses providing a list of sections."""

    __used_for__ = ISection

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


class SectionAddView(AddView):
    """A view for adding Sections."""

    def newSectionId(self):
        app = ISchoolToolApplication(None)
        sections = sorted(app['sections'].keys())
        if len(sections) == 0:
            return "1"

        name = sections[-1]
        try:
            name = str(int(name)+1)
        except ValueError:
            name = INameChooser(app['sections']).chooseName(name, None)
        return name

    def getCourseFromId(self, cid):
        app = ISchoolToolApplication(None)
        try:
            return app['courses'][cid]
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
        id = self.newSectionId()
        section = Section(title=id)
        self.context.add(section)
        self.course.sections.add(section)
        section.title = "%s (%s)" % (self.course.title, id)
        self.request.response.redirect(absoluteURL(section, self.request))


class SectionEditView(BaseEditView):
    """View for editing Sections."""

    __used_for__ = ISection


class ConflictDisplayMixin(TimetableConflictMixin):
    """A mixin for use in views that display event conflicts."""

    def __init__(self, context):
        self.context = context

    def getConflictingSections(self, item):
        """Return a sequence of sections that conflict with item.

        update(), which sets self.busy_periods, should be called before
        invoking this method.
        """
        result = []
        for section in self.getSections(item):
            if same(section, self.context):
                continue
            for (day_id, period_id), sections in self.busy_periods:
                if section in sections:
                    result.append({'day_id': day_id,
                                   'period_id': period_id,
                                   'section': section})
        result.sort(key=lambda x: (x['day_id'], x['period_id'],
                                   x['section'].label))
        return result

    def getSections(self, items):
        raise NotImplementedError("Subclasses should override this method.")

    @collect
    def _findConflicts(self, timetable_events, calendar_events):
        """Returns calendar events that intersect with section timetable events.

        This method expects timetable_events list to be ordered by dtstart.
        """
        calendar_events = sorted(calendar_events, reverse=True)
        def before(a, b):
            return (a.dtstart + a.duration) <= b.dtstart

        for ttevent in timetable_events:
            while calendar_events:
                if before(ttevent, calendar_events[-1]):
                    break
                elif before(calendar_events[-1], ttevent):
                    calendar_events.pop()
                else:
                    # conflict!
                    yield calendar_events.pop()

    def _groupConflicts(self, conflicts):
        """Generate a list of unique events out of a list of expanded events."""
        uniques = {}
        for event in conflicts:
            uniques.setdefault(event.unique_id, event)
        return uniques.values()

    def getConflictingEvents(self, item):
        """Return a list of conflicting events.

        Conflicting events are events that occur in the item calendar
        at some time that is booked/taken by section timetable event.
        """
        calendar = ISchoolToolCalendar(item)
        ctt = ICompositeTimetables(self.context)

        timetable_events = sorted(ctt.makeTimetableCalendar())

        if not timetable_events:
            return []

        first = timetable_events[0]
        last = timetable_events[-1]
        calendar_events = calendar.expand(first.dtstart,
                                          last.dtstart + last.duration)

        conflicts = self._findConflicts(timetable_events, calendar_events)

        return self._groupConflicts(conflicts)

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

    def getSections(self, item):
        return [section for section in getRelatedObjects(item, URISection)
                if ISection.providedBy(section)]

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

    def getSections(self, item):
        return [section for section in getRelatedObjects(item, URIGroup)
                if ISection.providedBy(section)]

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

    def getSections(self, item):
        return [section for section in getRelatedObjects(item, URIGroup)
                if ISection.providedBy(section)]

    def getCollection(self):
        return self.context.members

    def getSelectedItems(self):
        """Return a list of selected members."""
        return filter(IGroup.providedBy, self.getCollection())

    def getAvailableItemsContainer(self):
        return ISchoolToolApplication(None)['groups']


class SectionResourceView(RelationshipEditConfView):
    """View for adding learners to a Section."""

    __used_for__ = ISection

    title = _("Resources")
    current_title = _("Current Resources")
    available_title = _("Available Resources")

    def getSections(self, item):
        return getRelatedObjects(item, booking.URISection)

    def getCollection(self):
        return self.context.resources

    def getAvailableItemsContainer(self):
        return ISchoolToolApplication(None)['resources']
