"""
SchoolBell 0.8/0.9 exporter.

Hook up to a SchoolBell 0.8/0.9 Data.fs and dump everything we need (or can
use) to populate a SchoolBell 1.0 instance.

Using:

    python schoolbell-export.py <dbpath> <outfile> <caldir>

    <dbpath>  The full path to the 0.8/0.9 Data.fs
    <outfile> A file to dump the exported data to
    <caldir>  A directory to dump the icalendar files to

Note:

    You will need to setup your PYTHONPATH environment variable to include
    the SchoolBell-0.8/0.9 and Zope3 libs.

"""

import sys
import base64
from datetime import datetime

from xml.sax.saxutils import XMLGenerator
from xml.sax.xmlreader import AttributesNSImpl

try:
    from ZODB import DB
    from ZODB.FileStorage import FileStorage
    from schooltool.component import getRelatedObjects
    from schooltool.uris import URIMembership, URIGroup, URIMember
    from schooltool.icalendar import ical_text, ical_duration
except ImportError, e:
    print 'ImportError: %s' % e
    print "Please check your PYTHONPATH."
    sys.exit(1)


if len(sys.argv) < 4:
    print """Not enough arguments:

    python schoolbell-export.py <dbpath> <outfile> <caldir>

    <dbpath>  The full path to the 0.8/0.9 Data.fs
    <outfile> A file to dump the exported data to
    <caldir>  A directory to dump the icalendar files to
    """
    sys.exit(1)


class XMLWriter:
    """A utility class for writing our XML."""

    def __init__(self, output, encoding, app, version):
        writer = XMLGenerator(output, encoding)
        writer.startDocument()
        attr_values = {
            (None, u'version'): version,
            (None, u'app'): app,
        }
        attr_qnames = {
            (None, u'version'): u'version',
            (None, u'app'): u'app'
        }
        attrs = AttributesNSImpl(attr_values, attr_qnames)
        writer.startElementNS((None, u'schooltool'), u'schooltool', attrs)
        self._writer = writer
        self._output = output
        self._encoding = encoding

    def openTag(self, tag, attrs={}):
        att = self.createAttributes(attrs)
        self._writer.startElementNS((None, tag), tag, att)

    def closeTag(self, tag):
        self._writer.endElementNS((None, tag), tag)

    def simpleTag(self, tag, attrs=None):
        self.openTag(tag, attrs)
        self.closeTag(tag)

    def writeTag(self, tag, attrs):
        """Write an object to the..er..writer."""
        self.openTag(tag, attrs)
        self.closeTag(tag)

    def createAttributes(self, attrs={}):
        """A utility to create acceptable attributes for a tag."""
        values = {}
        qnames = {}

        for k,v in attrs.items():
            qnames[(None, k)] = k
            values[(None, k)] = v

        attributes = AttributesNSImpl(values, qnames)
        return attributes

    def close(self):
        """Clean things up and shut down."""
        self.closeTag('schooltool')
        self._writer.endDocument()


def setUpApplication(dbpath):
    """Get the SchoolBell application object out of the database."""

    storage = FileStorage(dbpath)
    db = DB(storage)
    conn = db.open()
    root = conn.root()
    app = root['schooltool']
    return app


def getCalendarText(calendar):
    dtstamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    result = [
        "BEGIN:VCALENDAR",
        "PRODID:-//SchoolTool.org/NONSGML SchoolTool//EN",
        "VERSION:2.0",
    ]
    events = list(calendar)
    events.sort()
    for event in events:
        title = event.title or ""
        location = event.location

        result += [
            "BEGIN:VEVENT",
            "UID:%s" % ical_text(event.unique_id),
            "SUMMARY:%s" % ical_text(title)]
        if location is not None:
            result.append("LOCATION:%s" % ical_text(location))
        if event.recurrence is not None:
            start = event.dtstart
            result.extend(event.recurrence.iCalRepresentation(start))
        privacy_map = {'private': 'PRIVATE', 'public' : 'PUBLIC',
                       'hidden': 'X-HIDDEN'}
        result += [
            "DTSTART:%s" % event.dtstart.strftime('%Y%m%dT%H%M%S'),
            "DURATION:%s" % ical_duration(event.duration),
            "DTSTAMP:%s" % dtstamp,
            "CLASS:%s" % privacy_map[event.privacy],
            "END:VEVENT",
        ]
    if not events:
        # There were no events.  iCalendar spec (RFC 2445) requires
        # VCALENDAR to have at least one subcomponent.  Let's create
        # a fake event.
        # NB Mozilla Calendar produces a 0-length file when publishing
        # empty calendars.  Sadly it does not then accept them
        # (http://bugzilla.mozilla.org/show_bug.cgi?id=229266).
        result += [
            "BEGIN:VEVENT",
            "UID:placeholder-nobody@localhost",
            "SUMMARY:%s" % ical_text("Empty calendar"),
            "DTSTART;VALUE=DATE:%s" % dtstamp[:8],
            "DTSTAMP:%s" % dtstamp,
            "END:VEVENT",
        ]
    result.append("END:VCALENDAR")

    return "\r\n".join(result)

def dumpCalendar(filename, obj):
    outfile = file(filename, 'w')
    outfile.write(getCalendarText(obj.calendar))
    outfile.close()

def exportPerson(person):
    password = ''
    if person.hasPassword():
        password = base64.encodestring(str(person._pwhash))[:-1]

    writer.openTag('person', {
            'username': person.username,
            'title': person.title,
            'path': '/persons/' + person.username,
            'password': password
            })

    groups = getRelatedObjects(person, URIGroup)
    for group in groups:
        writer.simpleTag('relationship',
                {'uri': 'URIGroup',
                'target': group.__name__}
                )

    writer.closeTag('person')

    dumpCalendar('%s/person.%s.ics' % (calpath, person.username), person)

def exportGroup(group):
    """Export a group."""

    # Note:Groups in 0.9 can be members of other groups, but we are not using
    # this in 1.0 so we won't bother to export it.
    writer.simpleTag('group', {
            'name': group.__name__,
            'title': group.title,
            'path': '/groups/' + group.__name__
            })
    dumpCalendar('%s/group.%s.ics' % (calpath, group.__name__), group)

def exportResource(resource):
    writer.openTag('resource', {
            'name': resource.__name__,
            'title': resource.title,
            'path': '/resources/' + resource.__name__
            })

    groups = getRelatedObjects(resource, URIGroup)
    for group in groups:
        writer.simpleTag('relationship',
                {'uri': 'URIGroup',
                'target': group.__name__}
                )

    writer.closeTag('resource')
    dumpCalendar('%s/resource.%s.ics' % (calpath, resource.__name__), resource)


if __name__ == '__main__':
    dbpath = sys.argv[1]
    xmlout = file(sys.argv[2], 'w')
    calpath = sys.argv[3]
    app = setUpApplication(dbpath)
    writer = XMLWriter(xmlout, 'utf-8', 'schoolbell', '0.9')

    for person in app['persons'].itervalues():
        exportPerson(person)

    for group in app['groups'].itervalues():
        exportGroup(group)

    for resource in app['resources'].itervalues():
        exportResource(resource)

    writer.close()
