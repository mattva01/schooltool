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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""Dashboard Implementation
"""
__docformat__ = 'reStructuredText'
import zope.component
import zope.interface
from zope.viewlet import manager, viewlet
from zope.traversing.browser.absoluteurl import absoluteURL

import schooltool.person
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.dashboard import interfaces
from schooltool.securitypolicy.crowds import TeachersCrowd, StudentsCrowd


class Dashboard(manager.ViewletManagerBase):
    zope.interface.implements(interfaces.IDashboard)

    table = None

    def __getitem__(self, name):
        """See zope.interface.common.mapping.IReadMapping"""
        viewlet = super(Dashboard, self).__getitem__(name)
        if not viewlet.isAvailable():
            raise zope.component.interfaces.ComponentLookupError(
                'Viewlet `%s` is not available.' %name)

    def createTable(self):
        self.table = [[], []]
        for index in range(len(self.viewlets)):
            try:
                html = {'title':self.viewlets[index].title,
                        'content':self.viewlets[index].render()}
            except Exception, e:
                html = {'title':self.viewlets[index].title,
                        'error':"An %s error occurred: %s" %
                        (e.__class__.__name__, str(e))}
            self.table[index%2].append(html)

    def filter(self, viewlets):
        """Filter by by availability."""
        viewlets = super(Dashboard, self).filter(viewlets)
        return [(name, viewlet) for name, viewlet in viewlets
                if viewlet.isAvailable()]

    def sort(self, viewlets):
        """Sort the viewlets by weight."""
        return sorted(viewlets, key=lambda v: v[1].getWeight())

    def update(self):
        super(Dashboard, self).update()
        self.createTable()

class DashboardTabView(object):

    def dynamicVariables(self):
        return """
            var ajaxURL = '%s/dashboardContent';
            """ % (absoluteURL(ISchoolToolApplication(None), self.request))


class DashboardCategory(viewlet.ViewletBase):
    zope.interface.implements(interfaces.IDashboardCategory)

    groups = []
    weight = 100

    # See interfaces.IDashboardCategory
    title = ''

    def appURL(self):
        return absoluteURL(ISchoolToolApplication(None), self.request)

    def getWeight(self):
        """See interfaces.IDashboardCategory"""
        return int(self.weight)

    def isAvailable(self):
        return True


class PersonDashboardCategory(DashboardCategory):
    """A person-centric dashboard category.

    It is aware of person objects, and is only available for
    schooltool users.
    """

    def __init__(self, context, request, view, manager):
        super(PersonDashboardCategory, self).__init__(context, request,
                                                      view, manager)
        # Since unauthenticated users cannot be adapted to Person object,
        # we must catch the exception
        try:
            self.context = schooltool.person.interfaces.IPerson(self.request.principal)
        except TypeError:
            self.context = None

    def isAvailable(self):
        return self.context != None

class SectionsCategory(PersonDashboardCategory):
    """Dashboard area for the user's sections"""
    @property
    def isTeacher(self):
        return TeachersCrowd(self.context).contains(self.request.principal)

    @property
    def isStudent(self):
        return StudentsCrowd(self.context).contains(self.request.principal)

    def getSections(self):
        person = schooltool.person.interfaces.IPerson(self.request.principal)
        instructor_of = schooltool.course.interfaces.IInstructor(person).sections()
        for section in instructor_of:
            url = absoluteURL(section, self.request)
            url += '/gradebook'
            title = '%s %s' % (list(section.courses)[0].title, section.title)
            yield {'url': url, 'title': title}
        learner_of = schooltool.course.interfaces.ILearner(person).sections()
        for section in learner_of:
            url = absoluteURL(section, self.request)
            url += '/mygrades'
            title = '%s %s' % (list(section.courses)[0].title, section.title)
            yield {'url': url, 'title': title}
