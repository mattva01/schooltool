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
from zope.component import adapts
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.app.container.interfaces import INameChooser
from zope.app.intid.interfaces import IIntIds
from zope.app.form.browser.add import AddView
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.publisher.browser import BrowserView
from zope.security.proxy import removeSecurityProxy
from zope.traversing.browser.interfaces import IAbsoluteURL
from zope.traversing.browser.absoluteurl import absoluteURL

from schooltool.term.interfaces import ITermContainer
from schooltool.schoolyear.interfaces import ISchoolYear
from schooltool.skin.containers import ContainerView
from schooltool.course.interfaces import ISectionContainer
from schooltool.course.interfaces import ICourse, ICourseContainer, ISection
from schooltool.app.relationships import URIInstruction, URISection
from schooltool.app.membership import URIGroup, URIMembership
from schooltool.relationship import getRelatedObjects

from schooltool.common import SchoolToolMessage as _


class CourseContainerAbsoluteURLAdapter(BrowserView):

    adapts(ICourseContainer, IBrowserRequest)
    implements(IAbsoluteURL)

    def __str__(self):
        container_id = int(self.context.__name__)
        int_ids = getUtility(IIntIds)
        container = int_ids.getObject(container_id)
        url = str(getMultiAdapter((container, self.request), name='absolute_url'))
        return url + '/courses'

    __call__ = __str__


class CourseContainerView(ContainerView):
    """A Course Container view."""

    __used_for__ = ICourseContainer

    index_title = _("Course index")

    @property
    def school_year(self):
        return ISchoolYear(self.context)


from schooltool.course.section import Section

class CourseView(BrowserView):
    """A view for courses."""

    __used_for__ = ICourse

    @property
    def school_year(self):
        return ISchoolYear(self.context)

    @property
    def terms(self):
        return ITermContainer(self.context)

    @property
    def details(self):
        details = []
        for name in ['course_id', 'government_id', 'credits']:
            value = getattr(self.context, name)
            if value is not None and unicode(value).strip():
                details.append({
                    'title': ICourse[name].title,
                    'value': value,
                    })
        return details

    def addSection(self, term):
        sections = ISectionContainer(term)
        section = Section()

        chooser = INameChooser(sections)
        name = chooser.chooseName('', section)
        sections[name] = section
        removeSecurityProxy(self.context).sections.add(section)
        section.title = "%s (%s)" % (self.context.title, section.__name__)
        return section

    def update(self):
        if 'ADD_SECTION' in self.request:
            term_id = self.request.get('term', None)
            if term_id is None:
                self.error = _("Please select a term.")
                return

            term = self.terms.get(term_id, None)
            if term is None:
                self.error = _("Selected term does not exist.")
                return

            section = self.addSection(term)
            self.request.response.redirect(absoluteURL(section, self.request))

    def __call__(self):
        self.update()
        return self.index()


class CourseAddView(AddView):
    """A view for adding Courses."""

    def nextURL(self):
        return absoluteURL(self.context.context, self.request)

    def update(self):
        if 'CANCEL' in self.request:
            self.request.response.redirect(self.nextURL())
        else:
            return AddView.update(self)


class CoursesViewlet(BrowserView):
    """A viewlet showing the courses a person is in."""

    def isTeacher(self):
        """Find out if the person is an instructor for any sections."""
        return len(self.instructorOf()) > 0

    def isLearner(self):
        """Find out if the person is a member of any sections."""
        return len(self.learnerOf()) > 0

    def instructorOf(self):
        """Get the sections the person instructs."""
        sections = getRelatedObjects(self.context, URISection,
                                     rel_type=URIInstruction)
        results = []
        for section in sections:
            results.append({'title': removeSecurityProxy(section).title,
                            'section': section})
        results.sort(key=lambda s: s['section'].__name__)
        return results

    def memberOf(self):
        """Seperate out generic groups from sections."""
        sections =  [group for group in self.context.groups
                     if not ISection.providedBy(group)]
        sections.sort(key=lambda s: s.__name__)
        return sections

    def learnerOf(self):
        """Get the sections the person is a member of."""
        results = []

        for item in self.context.groups:
            if ISection.providedBy(item):
                results.append({'section': item, 'group': None})
            else:
                group_sections = getRelatedObjects(item, URIGroup,
                                                   rel_type=URIMembership)
                for section in group_sections:
                    results.append({'section': section, 'group': item})
        results.sort(key=lambda s: s['section'].__name__)
        return results
