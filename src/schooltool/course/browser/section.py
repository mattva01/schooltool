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
from sets import Set

from zope.security.proxy import removeSecurityProxy
from zope.security.checker import canWrite
from zope.app import zapi
from zope.app.component.hooks import getSite
from zope.app.form.browser.add import AddView
from zope.app.form.interfaces import WidgetsError
from zope.app.form.utility import getWidgetsData
from zope.publisher.browser import BrowserView

from schooltool.person.interfaces import IPerson
from schooltool.group.interfaces import IGroup
from schooltool.batching import Batch
from schooltool.timetable.interfaces import ITimetables
from schooltool.app.browser.app import ContainerView, BaseEditView
from schooltool.group.interfaces import IGroup
from schooltool.person.interfaces import IPerson

from schooltool import SchoolToolMessage as _
from schooltool.app.app import getSchoolToolApplication
from schooltool.course.interfaces import ISection, ISectionContainer


class SectionContainerView(ContainerView):
    """A Course Container view."""

    __used_for__ = ISectionContainer

    index_title = _("Section index")
    add_title = _("Add a new section")
    add_url = "+/addSchoolToolSection.html"

    # XXX: very hacky, but necessary for now. :-(
    def getTimetables(self, obj):
        return ITimetables(obj).timetables


class SectionView(BrowserView):
    """A view for courses providing a list of sections."""

    __used_for__ = ISection

    def getPersons(self):
        return filter(IPerson.providedBy, self.context.members)

    def getGroups(self):
        return filter(IGroup.providedBy, self.context.members)


class SectionAddView(AddView):
    """A view for adding Sections."""

    error = None
    course = None

    def validCourse(self):
        return self.course is not None

    def getCourseFromId(self, cid):
        app = getSite()
        try:
            return app['courses'][cid]
        except KeyError:
            self.error = _("No such course.")

    def __init__(self, context, request):
        super(AddView, self).__init__(context, request)
        self.update_status = None
        self.errors = None

        try:
            course_id = request['field.course_id']
        except KeyError:
            self.error = _("Need a course ID.")
            return

        self.course = self.getCourseFromId(course_id)
        if self.course is not None:
            self.label = _("Add a Section to ${course}",
                           mapping={'course': self.course.title})

    def update(self):
        if self.update_status is not None:
            # We've been called before. Just return the previous result.
            return self.update_status

        if "UPDATE_SUBMIT" in self.request:
            self.update_status = ''
            try:
                data = getWidgetsData(self, self.schema, names=self.fieldNames)
                section = removeSecurityProxy(self.createAndAdd(data))
                self.course.sections.add(section)
            except WidgetsError, errors:
                self.errors = errors
                self.update_status = _("An error occurred.")
                return self.update_status

            self.request.response.redirect(self.nextURL())

        if 'CANCEL' in self.request:
            url = zapi.absoluteURL(self.course, self.request)
            self.request.response.redirect(url)

        return self.update_status

    def nextURL(self):
        return zapi.absoluteURL(self.course, self.request)


class SectionEditView(BaseEditView):
    """View for editing Sections."""

    __used_for__ = ISection


class RelationshipEditingViewBase(BrowserView):

    def add(self, item):
        """Add an item to the list of selected items."""
        # Only those who can edit this section will see the view so it
        # is safe to remove the security proxy here
        collection = removeSecurityProxy(self.getCollection())
        collection.add(item)

    def remove(self, item):
        """Remove an item from selected items."""
        # Only those who can edit this section will see the view so it
        # is safe to remove the security proxy here
        collection = removeSecurityProxy(self.getCollection())
        collection.remove(item)

    def getCollection(self):
        """Return the backend storage for related objects."""
        raise NotImplementedError("Subclasses should override this method.")

    def getSelectedItems(self):
        """Return a sequence of items that are already selected."""
        return self.getCollection()

    def getAvailableItems(self):
        """Return a sequence of items that can be selected."""
        raise NotImplementedError("Subclasses should override this method.")

    def update(self):
        # This method is rather similar to GroupListView.update().
        context_url = zapi.absoluteURL(self.context, self.request)
        if 'ADD_ITEMS' in self.request:
            for item in self.getAvailableItems():
                if 'add_item.' + item.__name__ in self.request:
                    item = removeSecurityProxy(item)
                    self.add(item)
        elif 'REMOVE_ITEMS' in self.request:
            for item in self.getSelectedItems():
                if 'remove_item.' + item.__name__ in self.request:
                    item = removeSecurityProxy(item)
                    self.remove(item)
        elif 'CANCEL' in self.request:
            self.request.response.redirect(context_url)

        if 'SEARCH' in self.request and 'CLEAR_SEARCH' not in self.request:
            searchstr = self.request['SEARCH'].lower()
            results = [item for item in self.getAvailableItems()
                       if searchstr in item.title.lower()]
        else:
            self.request.form['SEARCH'] = ''
            results = self.getAvailableItems()

        start = int(self.request.get('batch_start', 0))
        size = int(self.request.get('batch_size', 10))
        self.batch = Batch(results, start, size, sort_by='title')


class SectionInstructorView(RelationshipEditingViewBase):
    """View for adding instructors to a Section."""

    __used_for__ = ISection

    title = _("Instructors")
    current_title = _("Current Instructors")
    available_title = _("Available Instructors")

    def getCollection(self):
        return self.context.instructors

    def getAvailableItems(self):
        """Return a list of all possible members."""
        container = getSchoolToolApplication()['persons']
        selected_items = Set(self.getSelectedItems())
        return [p for p in container.values()
                if p not in selected_items]


class SectionLearnerView(RelationshipEditingViewBase):
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

    def getAvailableItems(self):
        """Return a list of all possible members."""
        container = getSchoolToolApplication()['persons']
        selected_items = Set(self.getSelectedItems())
        return [p for p in container.values()
                if p not in selected_items]


class SectionLearnerGroupView(RelationshipEditingViewBase):
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

    def getAvailableItems(self):
        """Return a list of all possible members."""
        container = getSchoolToolApplication()['groups']
        selected_items = Set(self.getSelectedItems())
        return [p for p in container.values()
                if p not in selected_items]


class SectionResourceView(RelationshipEditingViewBase):
    """View for adding learners to a Section."""

    __used_for__ = ISection

    title = _("Resources")
    current_title = _("Current Resources")
    available_title = _("Available Resources")

    def getCollection(self):
        return self.context.resources

    def getAvailableItems(self):
        """Return a list of all possible members."""
        container = getSchoolToolApplication()['resources']
        selected_items = Set(self.getSelectedItems())
        return [p for p in container.values()
                if p not in selected_items]
