"""
High-level setup functions for functional tests.

$Id$
"""

from zope.testbrowser.testing import Browser


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
    browser = Browser()
    browser.handleErrors = False
    browser.open('http://localhost/')
    browser.getLink('Log In').click()
    browser.getControl('Username').value = username
    browser.getControl('Password').value = password
    browser.getControl('Log in').click()
    assert 'Log Out' in browser.contents
    return browser


def addPerson(name, username=None, password=None, groups=None, browser=None):
    """Add a person.

    If username is not specified, it will be taken to be name.lower().

    If password is not specified, it will be taken to be username + 'pwd'.
    """
    if not username:
        username = name.lower()
    if not password:
        password = username + 'pwd'
    if browser is None:
        browser = logInManager()
    browser.getLink('Persons').click()
    browser.getLink('New Person').click()
    browser.getControl('Full name').value = name
    browser.getControl('Username').value = username
    browser.getControl('Password').value = password
    browser.getControl('Verify password').value = password
    browser.getControl('Add').click()

    if groups:
        browser.open('http://localhost/persons/%s' % username)
        browser.getLink('edit groups').click()
        for group in groups:
            browser.getControl(name='add_item.%s' % group).value = True
        browser.getControl('Add').click()
    browser.open('http://localhost/persons')

def addResource(title):
    """Add a resource."""
    manager = logInManager()
    manager.getLink('Resources').click()
    manager.getLink('New Resource').click()
    manager.getControl('Title').value = title
    manager.getControl('Add').click()
    manager.getControl('Type').value = ['resource']
    manager.getControl('Search').click()
    assert title in manager.contents


def setUpTimetabling(username):
    """Create the infrastructure for functional tests involving timetables.

    Creates it for the given user.
    """

    # We will need a term and a School timetable:
    manager = logInManager()
    manager.getLink('Terms').click()
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
    manager.getControl('Identifier').value = 'history6'
    manager.getControl('Description').value = 'History for the sixth class'
    manager.getControl('Add').click()

    # And a section:

    manager.getLink('History 6').click()
    manager.getLink('New Section').click()
    manager.getControl('Code').value = 'history-6a'
    manager.getControl('Identifier').value = 'history6a'
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
