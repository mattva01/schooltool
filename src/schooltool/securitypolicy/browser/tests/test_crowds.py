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
"""
Tests for registered security descriptions.
"""

import unittest
import doctest

from schooltool.schoolyear.testing import (setUp, tearDown,
                                           provideStubUtility,
                                           provideStubAdapter)
from schooltool.securitypolicy.ftesting import securitypolicy_functional_layer
from schooltool.securitypolicy.metaconfigure import getCrowdsUtility
from schooltool.securitypolicy.testing import (
    discriminator_sort_key,
    collectActionsByDiscriminator,
    printActionDescriptions,
    printDiscriminators)


def doctest_described_interfaces():
    r"""This is a crude attempt to list interfaces that are described in the
    security overview pages.

    First, collect interface/permission pairs with registered descriptions.

        >>> actions = collectActionsByDiscriminator()

        >>> sort_key = lambda i: discriminator_sort_key(i[0])
        >>> for discriminator, described in sorted(actions.items(),
        ...                                        key=sort_key):
        ...     print '%s: %s' % (
        ...         discriminator, [action.title for action in described])
        ('schooltool.edit', <...ISchoolToolApplication>):
            [u'Activate current school year',
        ...
             u'Modify']
        ('schooltool.view', <...ISchoolToolApplication>):
            [u'List', u'Access', u'View']
        ...
        ('schooltool.edit', <...IFieldDescription>):
            [u'Edit fields']
        ('schooltool.edit', <...ISchoolToolCalendar>):
            [u'Change calendar',
        ...

    Now, get the known crowds.

        >>> crowds = getCrowdsUtility().crowds.keys()

    And build sets of described and not described permission/interface pairs.

        >>> described = set(actions) & set(crowds)
        >>> missing = set(crowds) - set(actions)

    An interface/permission pair represents things the user can do in SchoolTool.

    Each interface/permission pair has a list of object/action pairs.
    The "object" is a rough approximation on SchoolTool object model from
    the user's perspective.  The "action" is an approximation of things user
    can do on the "object" if he has the required permission.

    Note the descriptions are sorted by modules of interfaces.  Some of the
    descriptions are declared in zcml, residing in other modules than the
    original interface.

    When you notice an "object" seemingly not belonging to the module of the
    interface (say, "Demographics"/"stuff" in schooltool.app.interfaces),
    this usually means one of the following:

    - The "object" has a functional extension on the described interface.

    - The "object" did not define it's own permissions and in reality inherits
      them from the parent.

    - There is a bug in zcml that registers the description.

        >>> described_actions = dict([
        ...     (discriminator, actions[discriminator])
        ...     for discriminator in described])

        >>> printActionDescriptions(described_actions)
        =========================
        schooltool.app.interfaces
        =========================
        - ISchoolToolApplication, schooltool.edit
        - ---------------------------------------
        -  School Years / Activate current school year
        -  Levels / Add/Remove
        -  School Years / Create/Delete
        -  Demographics / Manage
        -  SchoolTool application / Manage school settings and configuration
        -  Levels / Modify/Rename
        -  School Years / Modify
        -
        - ISchoolToolApplication, schooltool.view
        - ---------------------------------------
        -  School Years / List
        -  SchoolTool application / Access
        -  School Years / View
        -
        =================================
        schooltool.basicperson.interfaces
        =================================
        - IBasicPerson, schooltool.view
        - -----------------------------
        -  Messages / Browse other users' messages (overview)
        -
        - IFieldDescription, schooltool.edit
        - ----------------------------------
        -  Demographics / Edit fields
        -
        ==============================
        schooltool.calendar.interfaces
        ==============================
        - ISchoolToolCalendar, schooltool.edit
        - ------------------------------------
        -  SchoolTool application / Change calendar
        -  Sections / Change calendar
        -  Groups / Change calendar
        -  Users / Change calendar
        -  Reservations / Schedule reservation via calendar
        -
        - ISchoolToolCalendar, schooltool.view
        - ------------------------------------
        -  SchoolTool application / View calendar
        -  Sections / View calendar
        -  Groups / View calendar
        -  Users / View calendar
        -  Reservations / View reservation calendar
        -
        ==============================
        schooltool.contact.basicperson
        ==============================
        - IBoundContact, schooltool.view
        - ------------------------------
        -  Contacts / View user's contact information
        -
        =============================
        schooltool.contact.interfaces
        =============================
        - IContact, schooltool.edit
        - -------------------------
        -  Contacts / Modify an external contact
        -
        - IContact, schooltool.view
        - -------------------------
        -  Contacts / View an external contact
        -
        - IContactContainer, schooltool.edit
        - ----------------------------------
        -  Contacts / Create/Delete an external contact
        -
        - IContactContainer, schooltool.view
        - ----------------------------------
        -  Contacts / List/Search
        -
        ============================
        schooltool.course.interfaces
        ============================
        - ICourse, schooltool.edit
        - ------------------------
        -  Courses / Modify
        -
        - ICourse, schooltool.view
        - ------------------------
        -  Courses / View
        -
        - ICourseContainer, schooltool.edit
        - ---------------------------------
        -  Courses / Create/Delete
        -
        - ICourseContainer, schooltool.view
        - ---------------------------------
        -  Courses / List
        -
        - ISection, schooltool.edit
        - -------------------------
        -  Sections / Assign timetables
        -  Sections / Modify
        -
        - ISection, schooltool.view
        - -------------------------
        -  Sections / View
        -
        - ISectionContainer, schooltool.edit
        - ----------------------------------
        -  Sections / Create/Delete
        -
        - ISectionContainer, schooltool.view
        - ----------------------------------
        -  Sections / List
        -
        ===========================
        schooltool.group.interfaces
        ===========================
        - IGroup, schooltool.edit
        - -----------------------
        -  Groups / Modify
        -
        - IGroup, schooltool.view
        - -----------------------
        -  Groups / View
        -
        - IGroupContainer, schooltool.edit
        - --------------------------------
        -  Groups / Create/Delete
        -
        - IGroupContainer, schooltool.view
        - --------------------------------
        -  Groups / List
        -
        ============================
        schooltool.person.interfaces
        ============================
        - IPasswordWriter, schooltool.edit
        - --------------------------------
        -  Users / Change password
        -
        - IPerson, schooltool.edit
        - ------------------------
        -  Demographics / Modify user demographics
        -  Contacts / Manage user's contacts
        -  Contacts / Modify user's contact information
        -  Users / Modify
        -
        - IPerson, schooltool.editCalendarOverlays
        - ----------------------------------------
        -  Users / Manage visible calendars
        -
        - IPerson, schooltool.view
        - ------------------------
        -  Demographics / View user demographics
        -  Users / View
        -
        - IPersonContainer, schooltool.edit
        - ---------------------------------
        -  Users / Create/Delete
        -
        - IPersonContainer, schooltool.view
        - ---------------------------------
        -  Users / List/Search
        -
        - IPersonPreferences, schooltool.edit
        - -----------------------------------
        -  Users / Change preferences
        -
        - IPersonPreferences, schooltool.view
        - -----------------------------------
        -  Users / View preferences
        -
        ============================
        schooltool.report.interfaces
        ============================
        - IReportMessage, schooltool.view
        - -------------------------------
        -  Messages / Download reports
        -
        ==============================
        schooltool.resource.interfaces
        ==============================
        - IBaseResource, schooltool.edit
        - ------------------------------
        -  Reservations / Modify a resource
        -
        - IBaseResource, schooltool.view
        - ------------------------------
        -  Reservations / View a resource
        -
        - IResourceContainer, schooltool.edit
        - -----------------------------------
        -  Reservations / Add/Remove resources
        -
        - IResourceContainer, schooltool.view
        - -----------------------------------
        -  Reservations / List/Search resources
        -
        ==========================
        schooltool.task.interfaces
        ==========================
        - IMessage, schooltool.view
        - -------------------------
        -  Messages / Read messages
        -
        ==========================
        schooltool.term.interfaces
        ==========================
        - ITermContainer, schooltool.edit
        - -------------------------------
        -  Terms / Create/Delete
        -  Terms / Modify
        -
        - ITermContainer, schooltool.view
        - -------------------------------
        -  Terms / List
        -  Terms / View
        -
        ===============================
        schooltool.timetable.interfaces
        ===============================
        - IScheduleContainer, schooltool.edit
        - -----------------------------------
        -  Sections / Change schedule
        -
        - ITimetableContainer, schooltool.edit
        - ------------------------------------
        -  School timetables / Create/Delete
        -  School timetables / Modify
        -
        - ITimetableContainer, schooltool.view
        - ------------------------------------
        -  School timetables / List/Search
        -  School timetables / View
        -


    Some of the interface/permission pairs are intentionally (or by mistake!)
    not presented to the user.

        >>> printDiscriminators(missing)
        None, zope.ManageApplication
        None, zope.ManageContent
        None, zope.ManageServices
        None, zope.View
        None, zope.dublincore.change
        None, zope.dublincore.view
        -------------------------
        schooltool.app.interfaces
        -------------------------
        ISchoolToolApplication, zope.ManageSite
        ----------------------------
        schooltool.course.interfaces
        ----------------------------
        ICourseContainerContainer, schooltool.edit
        ----------------------------------
        schooltool.relationship.interfaces
        ----------------------------------
        IRelationshipLink, schooltool.edit
        IRelationshipLink, schooltool.view
        ----------------------------
        schooltool.report.interfaces
        ----------------------------
        IReportTask, schooltool.edit
        IReportTask, schooltool.view
        --------------------------
        schooltool.task.interfaces
        --------------------------
        IRemoteTask, schooltool.edit
        IRemoteTask, schooltool.view
        -------------------------------
        schooltool.timetable.interfaces
        -------------------------------
        IScheduleContainer, schooltool.view

        >>> print 'Total undescribed interface permissions: %d of %d (%d done)' % (
        ...     len(missing), len(crowds), len(actions))
        Total undescribed interface permissions: 15 of 57 (42 done)

    """


def test_suite():
    optionflags = (doctest.NORMALIZE_WHITESPACE |
                   doctest.ELLIPSIS |
                   doctest.REPORT_NDIFF)
    suite = doctest.DocTestSuite(optionflags=optionflags,
                                 extraglobs={'provideAdapter': provideStubAdapter,
                                             'provideUtility': provideStubUtility},
                                 setUp=setUp, tearDown=tearDown)
    suite.layer = securitypolicy_functional_layer
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
