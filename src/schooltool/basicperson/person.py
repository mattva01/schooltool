#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2007 Shuttleworth Foundation
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
Lyceum person specific code.

$Id$

"""
from zope.interface import implements
from zope.component import adapts
from zope.app.catalog.interfaces import ICatalog
from zope.app.catalog.catalog import Catalog
from zope.component import getUtility

from zc.catalog.catalogindex import ValueIndex

from schooltool.person.person import Person
from schooltool.person.interfaces import IPersonFactory
from schooltool.course.section import PersonInstructorsCrowd
from schooltool.person.person import PersonCalendarCrowd
from schooltool.table.table import IndexedLocaleAwareGetterColumn
from schooltool.utility.utility import UtilitySetUp
from schooltool.table.table import url_cell_formatter
from schooltool.relationship.interfaces import IRelationshipLinks

from schooltool.basicperson.advisor import Advising, URIAdvisor, URIAdvising, URIStudent
from schooltool.basicperson.interfaces import IAdvisor
from schooltool.basicperson.interfaces import IStudent
from schooltool.basicperson.interfaces import IBasicPerson
from schooltool import SchoolToolMessage as _


PERSON_CATALOG_KEY = 'schooltool.basicperson'


class BasicPerson(Person):
    implements(IBasicPerson)

    gender = None
    gradeclass = None
    birth_date = None

    def getAdvisor(self):
        return IStudent(self).advisor

    def setAdvisor(self, advisor):
        old_advisor = IStudent(self).advisor
        if old_advisor:
            IAdvisor(old_advisor).removeStudent(self)
        IAdvisor(advisor).addStudent(self)

    advisor = property(getAdvisor, setAdvisor)

    def __init__(self, username, first_name, last_name,
                 email=None, phone=None):
        self.first_name = first_name
        self.last_name = last_name
        self.username = username
        self.email = email
        self.phone = phone

    @property
    def title(self):
        return "%s %s" % (self.last_name, self.first_name)


class PersonFactoryUtility(object):

    implements(IPersonFactory)

    def columns(self):
        first_name = IndexedLocaleAwareGetterColumn(
            index='first_name',
            name='first_name',
            cell_formatter=url_cell_formatter,
            title=_(u'First Name'),
            getter=lambda i, f: i.first_name,
            subsort=True)
        last_name = IndexedLocaleAwareGetterColumn(
            index='last_name',
            name='last_name',
            cell_formatter=url_cell_formatter,
            title=_(u'Last Name'),
            getter=lambda i, f: i.last_name,
            subsort=True)

        return [first_name, last_name]

    def createManagerUser(self, username, system_name):
        return self(username, system_name, "Administrator")

    def sortOn(self):
        return (("last_name", False),)

    def groupBy(self):
        return (("grade", False),)

    def __call__(self, *args, **kw):
        result = BasicPerson(*args, **kw)
        return result


class BasicPersonCalendarCrowd(PersonCalendarCrowd):
    """Crowd that allows instructor of a person access persons calendar.

    XXX write functional test.
    """
    adapts(IBasicPerson)

    def contains(self, principal):
        return (PersonCalendarCrowd.contains(self, principal) or
                PersonInstructorsCrowd(self.context).contains(principal))


def catalogSetUp(catalog):
    catalog['__name__'] = ValueIndex('__name__', IBasicPerson)
    catalog['title'] = ValueIndex('title', IBasicPerson)
    catalog['first_name'] = ValueIndex('first_name', IBasicPerson)
    catalog['last_name'] = ValueIndex('last_name', IBasicPerson)


catalogSetUpSubscriber = UtilitySetUp(
    Catalog, ICatalog, PERSON_CATALOG_KEY, setUp=catalogSetUp)


def getPersonContainerCatalog(container):
    return getUtility(ICatalog, PERSON_CATALOG_KEY)
