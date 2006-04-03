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
Common code for functional tests.

$Id$
"""

def setUpTimetabling(manager, user, password):
    """Create the infrastructure for functional tests involving timetables.

    Creates a non admin user with given username and password.
    """

    manager.open('http://localhost/')
    assert 'SchoolTool' in manager.contents

    # Let's add a user:

    manager.getLink('Persons').click()
    manager.getLink('New Person').click()

    manager.getControl('Full name').value = 'Frog'
    manager.getControl('Username').value = user
    manager.getControl('Password').value = password
    manager.getControl('Verify password').value = password
    manager.getControl('Add').click()

    # We will need a term and a School timetable:

    manager.open('http://localhost/terms')
    manager.getLink('New Term').click()

    manager.getControl('Title').value = '2005 Fall'
    manager.getControl('Start date').value = '2005-09-01'
    manager.getControl('End date').value = '2006-01-31'
    manager.getControl('Next').click()


    manager.getControl('Sunday').click()
    manager.getControl('Saturday').click()
    manager.getControl('Add term').click()

    # Now the timetable:

    manager.open('http://localhost/ttschemas')
    manager.getLink('New Timetable').click()

    manager.getControl('Title').value = 'default'
    manager.getControl('Next').click()
    manager.getControl('Days of the week').click()
    manager.getControl('Same time each day').click()
    manager.getControl(name='field.times').value = """
       9:30-10:25
       10:30-11:25
       11:35-12:20
       12:45-13:30
       13:35-14:20
       14:30-15:15
    """
    manager.getControl('Next').click()
    manager.getControl('Designated by time').click()
    manager.getControl('No').click()

    # We will need a course:

    manager.open('http://localhost/courses')
    manager.getLink('New Course').click()

    manager.getControl('Title').value = 'History 6'
    manager.getControl('Description').value = 'History for the sixth class'
    manager.getControl('Add').click()

    # And a section:

    manager.getLink('History 6').click()
    manager.getLink('New Section').click()
    manager.getControl('Code').value = 'history-6a'
    manager.getControl('Description').value = 'History for the class 6A'
    manager.getControl('Add').click()

    # Let's assign Frog as a teacher for History 6:

    manager.getLink(url='http://localhost/sections/history6a').click()
    manager.getLink('edit instructors').click()
    manager.getControl('Frog').selected = True
    manager.getControl('Add').click()

    # And schedule the section:

    manager.open('http://localhost/sections/history6a')
    manager.getLink('Schedule').click()

    manager.getControl(name="Monday.09:30-10:25").value = True
    manager.getControl(name="Wednesday.11:35-12:20").value = True
    manager.getControl('Save').click()
