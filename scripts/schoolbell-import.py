"""
Import data from schoolbell-exporter.py to SchoolBell 1.0.

Creates a SchoolBell 1.0 Data.fs for migrating 0.8/0.9 data.

Using:

    python schoolbell-import.py <dbpath> <infile> <caldir>

    <dbpath>  The full path for the new 1.0 Data.fs
    <infile>  File containing data dumped from 0.8/0.9
    <caldir>  Directory containing the 0.8/0.9 icalendar files.

Note:

    You will need to setup your PYTHONPATH environment variable to include
    the SchoolBell-1.0 and Zope3 libs.

"""

import sys
import base64
from xml.dom import minidom
from xml import xpath

try:
    from ZODB import DB
    from ZODB.FileStorage import FileStorage
    from zope.app.publication.zopepublication import ZopePublication
    import transaction
    from schoolbell.app.main import bootstrapSchoolBell, configure
    from schoolbell.app.app import Person, Group, Resource
    from schoolbell.app.cal import Calendar, CalendarEvent
    from schoolbell.calendar.icalendar import read_icalendar
except ImportError, e:
    print 'ImportError: %s' % e
    print "Please check your PYTHONPATH."
    sys.exit(1)

if len(sys.argv) < 4:
    print """Not enough arguments:
    python schoolbell-import.py <dbpath> <infile> <caldir>

    <dbpath>  The full path for the new 1.0 Data.fs
    <infile>  File containing data dumped from 0.8/0.9
    <caldir>  Directory containing the 0.8/0.9 icalendar files.
    """
    sys.exit(1)


def setupOnePointZero(dbpath):
        storage = FileStorage(dbpath)
        db = DB(storage)

        configure()
        bootstrapSchoolBell(db)

        conn = db.open()
        root = conn.root()

        app = root.get(ZopePublication.root_name)

        return app

def importCalendar(obj, icalfile):
    events = read_icalendar(file(icalfile))

    cal = Calendar(obj)

    for event in events:
        cal.addEvent(
                CalendarEvent(
                    event.dtstart,
                    event.duration,
                    event.title,
                    location=event.location,
                    recurrence=event.recurrence,
                    unique_id=event.unique_id
                    )
                )

    obj.calendar = cal


if __name__ == '__main__':

    dbpath = sys.argv[1]
    infile = file(sys.argv[2], 'r')
    calpath = sys.argv[3]

    app = setupOnePointZero(dbpath)

    doc = minidom.parse(infile).documentElement

    for node in xpath.Evaluate('//group', doc):
        name = node.getAttribute('name')
        group = Group(node.getAttribute('title'))
        importCalendar(group, calpath + '/' + 'group.' + name + '.ics')
        app['groups'][name] = group

    for node in xpath.Evaluate('//person', doc):
        username = node.getAttribute('username')
        title = node.getAttribute('title')
        password = node.getAttribute('password')

        if username != 'manager':
            person = Person(username, title)
            if password:
                person._hashed_password = base64.decodestring(password)
            app['persons'][username] = person
        else:
            # Update the title "just in case"...
            app['persons']['manager'].title = title
            # Set the password
            if password:
                app['persons']['manager']._hashed_password \
                        = base64.decodestring(password)

        importCalendar(app['persons'][username],
                calpath + '/' + 'person.' + username + '.ics')


    for node in xpath.Evaluate('//resource', doc):
        name = node.getAttribute('name')
        resource = Resource(node.getAttribute('title'))

        importCalendar(resource, calpath + '/' + 'resource.' + name + '.ics')

        app['resources'][name] = resource

    for node in xpath.Evaluate('//person/relationship', doc):
        username = node.parentNode.getAttribute('username')
        person = app['persons'][username]

        if node.getAttribute('uri') == 'URIGroup':
            name = node.getAttribute('target')
            group = app['groups'][name]
            group.members.add(person)

    for node in xpath.Evaluate('//resource/relationship', doc):
        rname = node.parentNode.getAttribute('name')
        resource = app['resources'][rname]

        if node.getAttribute('uri') == 'URIGroup':
            gname = node.getAttribute('target')
            group = app['groups'][gname]
            group.members.add(resource)

    transaction.commit()
