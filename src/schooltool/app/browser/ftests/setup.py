"""
High-level setup functions for functional tests.
"""
from lxml import etree
from schooltool.testing.functional import TestBrowser
from zope.testbrowser.testing import Browser


def setUpBasicSchool():
    addSchoolYear('2005-2006', '2005-09-01', '2006-07-15')
    schoolyear = '2005-2006'
    addTerm('Fall', '2005-09-01', '2006-01-31', '2005-2006')
    addTerm('Spring', '2006-02-01', '2006-07-15', '2005-2006')


def logInManager():
    """Create a Browser instance and log in as a manager."""
    manager = Browser()
    manager.handleErrors = False
    manager.addHeader('Authorization', 'Basic manager:schooltool')
    manager.open('http://localhost/')
    assert 'SchoolTool' in manager.contents
    return manager


def logIn(username, password=None):
    """Create a Browser instance and log in."""
    if not password:
        password = username + 'pwd'
    browser = TestBrowser()
    browser.handleErrors = False
    browser.open('http://localhost/')
    browser.getLink('Log In').click()
    browser.getControl('Username').value = username
    browser.getControl('Password').value = password
    browser.getControl('Log in').click()
    assert 'Log Out' in browser.contents
    browser.username = username
    browser.password = password
    return browser


def addResource(title):
    """Add a resource."""
    manager = logInManager()
    manager.getLink('Manage').click()
    manager.getLink('Resources').click()
    manager.getLink('Add Resource').click()
    manager.getControl('Title').value = title
    manager.getControl('Add').click()
    manager.getLink('Resource', index=2).click()
    assert title in manager.contents

def addCourse(title, schoolyear, description=""):
    """Add a course."""
    manager = logInManager()
    manager.getLink('Manage').click()
    manager.getLink('School Years').click()
    manager.getLink(schoolyear).click()
    manager.getLink('Courses').click()
    manager.getLink('Add Course').click()
    manager.getControl('Title').value = title
    manager.getControl('Description').value = description
    manager.getControl('Add').click()

def addSection(course, schoolyear, term, title=None, instructors=[], members=[]):
    """Add a section."""
    manager = logInManager()
    manager.getLink('Manage').click()
    manager.getLink('School Years').click()
    manager.getLink(schoolyear).click()
    manager.getLink('Courses').click()
    manager.getLink(course).click()
    manager.getLink('Add Section').click()
    manager.getControl('Starts in term').displayValue = [term]
    manager.getControl('Ends in term').displayValue = [term]
    manager.getControl('Add').click()

    # XXX: boy oh boy, will this slow the tests down.
    #      Somebody should rewrite the whole method to use CSV import.
    doc = etree.HTML(manager.contents)
    links = doc.xpath("id('content-body')//a[contains(.,'%s')]/@href" % course)
    manager.getLink(url=sorted(links)[-1]).click()

    if title is not None:
        manager.getLink('Edit Info').click()
        manager.getControl('Title').value = title
        manager.getControl('Apply').click()
    manager.getLink('edit instructors').click()
    for instructor in instructors:
        manager.getControl(instructor).click()
    manager.getControl('Add').click()
    manager.getControl('OK').click()
    manager.getLink('edit individuals').click()
    for member in members:
        manager.getControl(member).click()
    manager.getControl('Add').click()
    manager.getControl('OK').click()

def addSchoolYear(title, first, last):
    manager = logInManager()
    manager.getLink('Manage').click()
    manager.getLink('School Years').click()
    manager.getLink('New School Year').click()
    manager.getControl('Title').value = title
    manager.getControl('First day').value = first
    manager.getControl('Last day').value = last
    manager.getControl('Add').click()

def addTerm(title, first, last, schoolyear):
    manager = logInManager()
    manager.getLink('Manage').click()
    manager.getLink('School Years').click()
    manager.getLink(schoolyear).click()

    manager.getLink('Add a new term').click()
    manager.getControl('Title').value = title
    manager.getControl('Start date').value = first
    manager.getControl('End date').value = last
    manager.getControl('Next').click()

    manager.getControl('Sunday').click()
    manager.getControl('Saturday').click()
    manager.getControl('Add term').click()


def addDefaultSchoolTimetable(schoolyear='2005-2006'):
    """Creates a school timetable used in some functional tests"""

    manager = logInManager()

    manager.getLink('Manage').click()
    manager.getLink('School Years').click()
    manager.getLink(schoolyear).click()
    manager.getLink('School Timetables').click()
    manager.getLink('New Timetable').click()
    manager.getLink('advanced adding form').click()

    manager.getControl('Title').value = 'schema1'
    manager.getControl('Add day').click()
    manager.getControl('Add period').click()

    manager.getControl(name='day1.period1').value = 'A'
    manager.getControl(name='day1.period2').value = 'B'
    manager.getControl(name='day2.period1').value = 'C'
    manager.getControl(name='day2.period2').value = 'D'
    manager.getControl('Timetable day always coincides with the day of week'
                       ' (i.e. on Mondays the first timetable day is used, on'
                       ' Tuesdays the second, and so on).').click()

    manager.getControl(name='time1.day0').value = '9:00'
    manager.getControl(name='time2.day0').value = '10:00'

    manager.getControl(name='time1.day1').value = '9:00'
    manager.getControl(name='time2.day1').value = '10:00'

    manager.getControl(name='time1.day2').value = '9:00'
    manager.getControl(name='time2.day2').value = '10:00'

    manager.getControl(name='time1.day3').value = '8:00'
    manager.getControl(name='time2.day3').value = '11:00'

    manager.getControl(name='time1.day4').value = '8:00'
    manager.getControl(name='time2.day4').value = '11:00'

    manager.getControl('Duration').value = '60'
    manager.getControl('Create timetable schema').click()



def setUpTimetabling(username):
    """Create the infrastructure for functional tests involving timetables.

    Creates it for the given user.
    """

    # We will need a schoolyear, a term and a School timetable:
    manager = logInManager()

    addSchoolYear('2005-2006', '2005-09-01', '2006-07-15')
    addTerm('2005 Fall', '2005-09-01', '2006-01-31', '2005-2006')

    # Now the timetable:

    manager.open('http://localhost/schoolyears/2005-2006/school_timetables')
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

    manager.open('http://localhost/schoolyears/2005-2006/courses')
    manager.getLink('Add Course').click()

    addCourse('History 6', '2005-2006', 'History for the sixth class')

    # And a section:
    addSection('History 6', '2005-2006', '2005 Fall')

    # Let's assign Frog as a teacher for History 6:

    manager.open('http://localhost/schoolyears/2005-2006/2005-fall/sections/1')
    manager.getLink('edit instructors').click()
    manager.getControl('Frog').selected = True
    manager.getControl('Add').click()

    # And schedule the section:

    manager.open('http://localhost/schoolyears/2005-2006/2005-fall/sections/1')
    manager.getLink('Schedule').click()
    manager.getLink('Add Timetable').click()
    manager.getControl('Add').click()
    manager.getControl(name="Monday.09:30-10:25").value = True
    manager.getControl(name="Wednesday.11:35-12:20").value = True
    manager.getControl('Save').click()
