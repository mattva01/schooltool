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
"""
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.interface import implements
from zope.component import adapts
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.intid.interfaces import IIntIds
from zope.app.form.browser.add import AddView
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.publisher.browser import BrowserView
from zope.security.proxy import removeSecurityProxy
from zope.traversing.browser.interfaces import IAbsoluteURL
from zope.traversing.browser.absoluteurl import absoluteURL
from zope.i18n.interfaces.locales import ICollator
from zope.viewlet.viewlet import ViewletBase

from schooltool.term.interfaces import ITerm
from schooltool.schoolyear.interfaces import ISchoolYear
from schooltool.skin.containers import ContainerView
from schooltool.course.interfaces import ICourse, ICourseContainer
from schooltool.course.interfaces import ILearner, IInstructor

from schooltool.common import SchoolToolMessage as _

from schooltool.skin.flourish.viewlet import Viewlet


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


class CourseView(BrowserView):
    """A view for courses."""

    __used_for__ = ICourse

    @property
    def school_year(self):
        return ISchoolYear(self.context)

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

    @property
    def sections(self):
        items = []
        for section in self.context.sections:
            term = ITerm(section, None)
            items.append({
                'section': section,
                'term': term,
                })
        def sortKey(item):
            # I consider it acceptable to violate security for sorting purposes
            # in this case.
            section = removeSecurityProxy(item['section'])
            term = removeSecurityProxy(item['term'])
            return u'%s%s%s' % (section.label,
                                term.first,
                                section.__name__)
        return sorted(items, key=sortKey)


class CourseAddView(AddView):
    """A view for adding Courses."""

    def nextURL(self):
        return absoluteURL(self.context.context, self.request)

    def update(self):
        if 'CANCEL' in self.request:
            self.request.response.redirect(self.nextURL())
        else:
            return AddView.update(self)


class CoursesViewlet(ViewletBase):
    """A viewlet showing the courses a person is in."""

    def __init__(self, *args, **kw):
        super(CoursesViewlet, self).__init__(*args, **kw)
        self.collator = ICollator(self.request.locale)

    def update(self):
        self.instructorOf = self.sectionsAsTeacher()
        self.learnerOf = self.sectionsAsLearner()

    def isTeacher(self):
        """Find out if the person is an instructor for any sections."""
        return bool(self.instructorOf)

    def isLearner(self):
        """Find out if the person is a member of any sections."""
        return bool(self.learnerOf)

    def sectionsAsTeacher(self):
        """Get the sections the person instructs."""
        return self.sectionsAs(IInstructor)

    def sectionsAsLearner(self):
        """Get the sections the person is a member of."""
        return self.sectionsAs(ILearner)

    def sectionsAs(self, role_interface):
        schoolyears_data = {}
        for section in role_interface(self.context).sections():
            sy = ISchoolYear(section)
            if sy not in schoolyears_data:
                schoolyears_data[sy] = {}
            term = ITerm(section)
            if term not in schoolyears_data[sy]:
                schoolyears_data[sy][term] = []
            schoolyears_data[sy][term].append(section)
        result = []
        for sy in sorted(schoolyears_data, key=lambda x:x.first, reverse=True):
            sy_info = {'obj': sy, 'terms': []}
            for term in sorted(schoolyears_data[sy], key=lambda x:x.first):
                sortingKey = lambda section:{'course':
                                             ', '.join([course.title
                                                        for course in
                                                        section.courses]),
                                             'section_title': section.title}
                term_info = {'obj': term, 'sections': []}
                for section in sorted(schoolyears_data[sy][term],
                                      cmp=self.sortByCourseAndSection,
                                      key=sortingKey):
                    section_info = {'obj': section,
                                    'title': '%s -- %s' % \
                                    (', '.join(course.title
                                               for course in section.courses),
                                     section.title)}
                    term_info['sections'].append(section_info)
                sy_info['terms'].append(term_info)
            result.append(sy_info)
        return result

    def sortByCourseAndSection(self, this, other):
        if this['course'] is other['course']:
            return self.collator.cmp(this['section_title'],
                                     other['section_title'])
        return self.collator.cmp(this['course'], other['course'])


class FlourishCoursesViewlet(Viewlet):
    """A flourish viewlet showing the courses a person is in."""

    template = ViewPageTemplateFile('templates/f_coursesviewlet.pt')
    body_template = None
    render = lambda self, *a, **kw: self.template(*a, **kw)

    def __init__(self, *args, **kw):
        super(FlourishCoursesViewlet, self).__init__(*args, **kw)
        self.collator = ICollator(self.request.locale)

    def update(self):
        self.instructorOf = self.sectionsAsTeacher()
        self.learnerOf = self.sectionsAsLearner()

    def isTeacher(self):
        """Find out if the person is an instructor for any sections."""
        return bool(self.instructorOf)

    def isLearner(self):
        """Find out if the person is a member of any sections."""
        return bool(self.learnerOf)

    def sectionsAsTeacher(self):
        """Get the sections the person instructs."""
        return self.sectionsAs(IInstructor)

    def sectionsAsLearner(self):
        """Get the sections the person is a member of."""
        return self.sectionsAs(ILearner)

    def sectionsAs(self, role_interface):
        schoolyears_data = {}
        for section in role_interface(self.context).sections():
            sy = ISchoolYear(section)
            if sy not in schoolyears_data:
                schoolyears_data[sy] = {}
            term = ITerm(section)
            if term not in schoolyears_data[sy]:
                schoolyears_data[sy][term] = []
            schoolyears_data[sy][term].append(section)
        result = []
        for sy in sorted(schoolyears_data, key=lambda x:x.first, reverse=True):
            sy_info = {'obj': sy, 'terms': []}
            for term in sorted(schoolyears_data[sy], key=lambda x:x.first):
                sortingKey = lambda section:{'course':
                                             ', '.join([course.title
                                                        for course in
                                                        section.courses]),
                                             'section_title': section.title}
                term_info = {'obj': term, 'sections': []}
                for section in sorted(schoolyears_data[sy][term],
                                      cmp=self.sortByCourseAndSection,
                                      key=sortingKey):
                    section_info = {'obj': section,
                                    'title': '%s -- %s' % \
                                    (', '.join(course.title
                                               for course in section.courses),
                                     section.title)}
                    term_info['sections'].append(section_info)
                sy_info['terms'].append(term_info)
            result.append(sy_info)
        return result

    def sortByCourseAndSection(self, this, other):
        if this['course'] is other['course']:
            return self.collator.cmp(this['section_title'],
                                     other['section_title'])
        return self.collator.cmp(this['course'], other['course'])

