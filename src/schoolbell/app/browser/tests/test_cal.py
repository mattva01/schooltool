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
Tests for SchoolBell calendaring views.

$Id$
"""

import unittest
from datetime import datetime, date, timedelta
from zope.testing import doctest
from zope.publisher.browser import TestRequest
from zope.interface import directlyProvides
from zope.interface.verify import verifyObject
from zope.app.tests import setup, ztapi
from zope.app.traversing.interfaces import IContainmentRoot


def doctest_CalendarOwnerTraverser():
    """Tests for CalendarOwnerTraverse.

    CalendarOwnerTraverser allows you to traverse directly to the calendar
    of a calendar owner.

        >>> from schoolbell.app.browser.cal import CalendarOwnerTraverser
        >>> from schoolbell.app.app import Person
        >>> person = Person()
        >>> request = TestRequest()
        >>> traverser = CalendarOwnerTraverser(person, request)
        >>> traverser.context is person
        True
        >>> traverser.request is request
        True

    The traverser should implement IBrowserPublisher:

        >>> from zope.publisher.interfaces.browser import IBrowserPublisher
        >>> verifyObject(IBrowserPublisher, traverser)
        True

    Let's check that browserDefault suggests 'index.html':

        >>> context, path = traverser.browserDefault(request)
        >>> context is person
        True
        >>> path
        ('index.html',)

    The whole point of this class is that we can ask for the calendar:

        >>> traverser.publishTraverse(request, 'calendar') is person.calendar
        True

    However, we should be able to access other views of the object:

        >>> from zope.app.publisher.browser import BrowserView
        >>> from schoolbell.app.interfaces import IPerson
        >>> ztapi.browserView(IPerson, 'some_view.html', BrowserView)

        >>> view = traverser.publishTraverse(request, 'some_view.html')
        >>> view.context is traverser.context
        True
        >>> view.request is traverser.request
        True

    If we try to look up a nonexistent view, we should get a NotFound error:

        >>> traverser.publishTraverse(request,
        ...                           'nonexistent.html') # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        NotFound: Object: <...Person object at ...>, name: 'nonexistent.html'

    """


def doctest_PlainCalendarView():
    """Tests for PlainCalendarView.

        >>> from schoolbell.app.browser.cal import PlainCalendarView
        >>> from schoolbell.app.app import Calendar
        >>> calendar = Calendar()
        >>> request = TestRequest()
        >>> view = PlainCalendarView(calendar, request)
        >>> view.update()
        >>> len(calendar)
        0

        >>> request = TestRequest()
        >>> request.form = {'GENERATE': ''}
        >>> view = PlainCalendarView(calendar, request)
        >>> view.update()
        >>> len(calendar) > 0
        True

    """


def doctest_CalendarDay():
    """A calendar day is a set of events that took place on a particular day.

        >>> from schoolbell.app.browser.cal import CalendarDay
        >>> day1 = CalendarDay(date(2004, 8, 5))
        >>> day2 = CalendarDay(date(2004, 7, 15), ["abc", "def"])
        >>> day1.date
        datetime.date(2004, 8, 5)
        >>> day1.events
        []
        >>> day2.date
        datetime.date(2004, 7, 15)
        >>> day2.events
        ['abc', 'def']

        >>> day1 > day2 and not day1 < day2
        True
        >>> day2 == CalendarDay(date(2004, 7, 15))
        True

    """


def createEvent(dtstart, duration, title, **kw):
    """Create a SimpleCalendarEvent.

      >>> from schoolbell.calendar.simple import SimpleCalendarEvent
      >>> e1 = createEvent('2004-01-02 14:45:50', '5min', 'title')
      >>> e1 == SimpleCalendarEvent(datetime(2004, 1, 2, 14, 45, 50),
      ...                timedelta(minutes=5), 'title', unique_id=e1.unique_id)
      True

      >>> e2 = createEvent('2004-01-02 14:45', '3h', 'title')
      >>> e2 == SimpleCalendarEvent(datetime(2004, 1, 2, 14, 45),
      ...                timedelta(hours=3), 'title', unique_id=e2.unique_id)
      True

      >>> e3 = createEvent('2004-01-02', '2d', 'title')
      >>> e3 == SimpleCalendarEvent(datetime(2004, 1, 2),
      ...                timedelta(days=2), 'title', unique_id=e3.unique_id)
      True

    createEvent is very strict about the format of it arguments, and terse in
    error reporting, but it's OK, as it is only used in unit tests.
    """
    from schoolbell.calendar.simple import SimpleCalendarEvent
    from schoolbell.calendar.utils import parse_datetime
    if dtstart.count(':') == 0:         # YYYY-MM-DD
        dtstart = parse_datetime(dtstart+' 00:00:00') # add hh:mm:ss
    elif dtstart.count(':') == 1:       # YYYY-MM-DD HH:MM
        dtstart = parse_datetime(dtstart+':00') # add seconds
    else:                               # YYYY-MM-DD HH:MM:SS
        dtstart = parse_datetime(dtstart)
    dur = timedelta(0)
    for part in duration.split('+'):
        part = part.strip()
        if part.endswith('d'):
            dur += timedelta(days=int(part.rstrip('d')))
        elif part.endswith('h'):
            dur += timedelta(hours=int(part.rstrip('h')))
        elif part.endswith('sec'):
            dur += timedelta(seconds=int(part.rstrip('sec')))
        else:
            dur += timedelta(minutes=int(part.rstrip('min')))
    return SimpleCalendarEvent(dtstart, dur, title, **kw)


class TestCalendarViewBase(unittest.TestCase):
    # Legacy unit tests from SchoolTool.

    def test_dayTitle(self):
        from schoolbell.app.browser.cal import CalendarViewBase
        view = CalendarViewBase(None, None)
        dt = datetime(2004, 7, 1)
        self.assertEquals(view.dayTitle(dt), "Thursday, 2004-07-01")

    def test_ellipsizeTitle(self):
        from schoolbell.app.browser.cal import CalendarViewBase

        under17 = '1234567890123456'
        over17 = '12345678901234567'

        view = CalendarViewBase(None, None)
        self.assertEquals(view.ellipsizeTitle(under17), under17)
        self.assertEquals(view.ellipsizeTitle(over17), '123456789012345...')

    def test_prev_next(self):
        from schoolbell.app.browser.cal import CalendarViewBase
        view = CalendarViewBase(None, None)
        view.cursor = date(2004, 8, 18)
        self.assertEquals(view.prevMonth(), date(2004, 7, 1))
        self.assertEquals(view.nextMonth(), date(2004, 9, 1))
        self.assertEquals(view.prevDay(), date(2004, 8, 17))
        self.assertEquals(view.nextDay(), date(2004, 8, 19))

    def test_getWeek(self):
        from schoolbell.app.browser.cal import CalendarViewBase, CalendarDay
        from schoolbell.app.app import Calendar

        cal = Calendar()
        view = CalendarViewBase(cal, None)
        self.assertEquals(view.first_day_of_week, 0) # Monday by default

        def getDaysStub(start, end):
            return [CalendarDay(start), CalendarDay(end)]
        view.getDays = getDaysStub

        for dt in (date(2004, 8, 9), date(2004, 8, 11), date(2004, 8, 15)):
            week = view.getWeek(dt)
            self.assertEquals(week,
                              [CalendarDay(date(2004, 8, 9)),
                               CalendarDay(date(2004, 8, 16))])

        dt = date(2004, 8, 16)
        week = view.getWeek(dt)
        self.assertEquals(week,
                          [CalendarDay(date(2004, 8, 16)),
                           CalendarDay(date(2004, 8, 23))])

    def test_getWeek_first_day_of_week(self):
        from schoolbell.app.browser.cal import CalendarViewBase, CalendarDay
        from schoolbell.app.app import Calendar

        cal = Calendar()
        view = CalendarViewBase(cal, None)
        view.first_day_of_week = 2 # Wednesday

        def getDaysStub(start, end):
            return [CalendarDay(start), CalendarDay(end)]
        view.getDays = getDaysStub

        for dt in (date(2004, 8, 11), date(2004, 8, 14), date(2004, 8, 17)):
            week = view.getWeek(dt)
            self.assertEquals(week, [CalendarDay(date(2004, 8, 11)),
                                     CalendarDay(date(2004, 8, 18))],
                              "%s: %s -- %s"
                              % (dt, week[0].date, week[1].date))

        dt = date(2004, 8, 10)
        week = view.getWeek(dt)
        self.assertEquals(week,
                          [CalendarDay(date(2004, 8, 4)),
                           CalendarDay(date(2004, 8, 11))])

        dt = date(2004, 8, 18)
        week = view.getWeek(dt)
        self.assertEquals(week,
                          [CalendarDay(date(2004, 8, 18)),
                           CalendarDay(date(2004, 8, 25))])

    def test_getMonth(self):
        from schoolbell.app.browser.cal import CalendarViewBase, CalendarDay
        from schoolbell.app.app import Calendar

        cal = Calendar()
        view = CalendarViewBase(cal, None)

        def getDaysStub(start, end):
            return [CalendarDay(start), CalendarDay(end)]
        view.getDays = getDaysStub

        weeks = view.getMonth(date(2004, 8, 11))
        self.assertEquals(len(weeks), 6)
        bounds = [(d1.date, d2.date) for d1, d2 in weeks]
        self.assertEquals(bounds,
                          [(date(2004, 7, 26), date(2004, 8, 2)),
                           (date(2004, 8, 2), date(2004, 8, 9)),
                           (date(2004, 8, 9), date(2004, 8, 16)),
                           (date(2004, 8, 16), date(2004, 8, 23)),
                           (date(2004, 8, 23), date(2004, 8, 30)),
                           (date(2004, 8, 30), date(2004, 9, 6))])

        # October 2004 ends with a Sunday, so we use it to check that
        # no days from the next month are included.
        weeks = view.getMonth(date(2004, 10, 1))
        bounds = [(d1.date, d2.date) for d1, d2 in weeks]
        self.assertEquals(bounds[4],
                          (date(2004, 10, 25), date(2004, 11, 1)))

        # Same here, just check the previous month.
        weeks = view.getMonth(date(2004, 11, 1))
        bounds = [(d1.date, d2.date) for d1, d2 in weeks]
        self.assertEquals(bounds[0],
                          (date(2004, 11, 1), date(2004, 11, 8)))

    def test_getYear(self):
        from schoolbell.app.browser.cal import CalendarViewBase, CalendarDay
        from schoolbell.app.app import Calendar

        cal = Calendar()
        view = CalendarViewBase(cal, None)

        def getMonthStub(dt):
            return dt
        view.getMonth = getMonthStub

        year = view.getYear(date(2004, 03, 04))
        self.assertEquals(len(year), 4)
        months = []
        for quarter in year:
            self.assertEquals(len(quarter), 3)
            months.extend(quarter)
        for i, month in enumerate(months):
            self.assertEquals(month, date(2004, i+1, 1))

    def assertEqualEventLists(self, result, expected):
        fmt = lambda x: '[%s]' % ', '.join([e.title for e in x])
        self.assertEquals(result, expected,
                          '%s != %s' % (fmt(result), fmt(expected)))

    def test_getDays(self):
        from schoolbell.app.browser.cal import CalendarViewBase
        from schoolbell.app.app import Calendar

        e0 = createEvent('2004-08-10 11:00', '1h', "e0")
        #e1 = createEvent('2004-08-11 12:00', '1h', "e1", privacy="hidden")
        e2 = createEvent('2004-08-11 11:00', '1h', "e2")
        e3 = createEvent('2004-08-12 23:00', '4h', "e3")
        e4 = createEvent('2004-08-15 11:00', '1h', "e4")
        e5 = createEvent('2004-08-10 09:00', '3d', "e5")
        e6 = createEvent('2004-08-13 00:00', '1d', "e6")
        e7 = createEvent('2004-08-12 00:00', '1d+1sec', "e7")
        e8 = createEvent('2004-08-15 00:00', '0sec', "e8")

        cal = Calendar()
#        for e in [e0, e1, e2, e3, e4, e5, e6, e7, e8]:
        for e in [e0, e2, e3, e4, e5, e6, e7, e8]:
            cal.addEvent(e)

        request = TestRequest()
        view = CalendarViewBase(cal, request)

        start = date(2004, 8, 10)
        days = view.getDays(start, start)
        self.assertEquals(len(days), 0)

        start = date(2004, 8, 10)
        end = date(2004, 8, 16)
        days = view.getDays(start, end)

        self.assertEquals(len(days), 6)
        for i, day in enumerate(days):
            self.assertEquals(day.date, date(2004, 8, 10 + i))

        self.assertEqualEventLists(days[0].events, [e5, e0])            # 10
#        self.assertEqualEventLists(days[1].events, [e5, e2, e1])        # 11
        self.assertEqualEventLists(days[1].events, [e5, e2])            # 11
        self.assertEqualEventLists(days[2].events, [e5, e7, e3])        # 12
        self.assertEqualEventLists(days[3].events, [e5, e7, e3, e6])    # 13
        self.assertEqualEventLists(days[4].events, [])                  # 14
        self.assertEqualEventLists(days[5].events, [e8, e4])            # 15

        start = date(2004, 8, 11)
        end = date(2004, 8, 12)
        days = view.getDays(start, end)
        self.assertEquals(len(days), 1)
        self.assertEquals(days[0].date, start)
#        self.assertEqualEventLists(days[0].events, [e5, e2, e1])
        self.assertEqualEventLists(days[0].events, [e5, e2])

        # TODO Disabled because we do not support hidden events yet.
        ## Check that the hidden event is excluded for another person
        #view.request = RequestStub(authenticated_user=self.person2)
        #start = date(2004, 8, 11)
        #end = date(2004, 8, 12)
        #days = view.getDays(start, end)

        #self.assertEqualEventLists(days[0].events, [e5, e2])            # 11


#
# XXX XMLCompareMixin and normalize_xml are used in TestCalendarEventView.
#     We might want to rewrite the tests or at least move these helpers
#     code somewhere else -- normalize_xml is huge.
#

class XMLCompareMixin(object):
    # XXX We might want to move this into some common module.

    def assertEqualsXML(self, result, expected, recursively_sort=()):
        """Assert that two XML documents are equivalent.

        If recursively_sort is given, it is a sequence of tags that
        will have test:sort="recursively" appended to their attribute lists
        in 'result' text.  See the docstring for normalize_xml for more
        information about this attribute.
        """
        import difflib
        result = normalize_xml(result, recursively_sort=recursively_sort)
        expected = normalize_xml(expected, recursively_sort=recursively_sort)
        self.assertEquals(result, expected,
                          "\n".join(difflib.ndiff(expected.split("\n"),
                                                  result.split("\n"))))


def normalize_xml(xml, recursively_sort=()):
    """Normalizes an XML document.

    The idea is that two semantically equivalent XML documents should be
    normalized into the same canonical representation.  Therefore if two
    documents compare equal after normalization, they are semantically
    equivalent.

    The canonical representation used here has nothing to do with W3C Canonical
    XML.

    This function normalizes indentation, whitespace and newlines (except
    inside text nodes), element attribute order, expands character references,
    expands shorthand notation of empty XML elements ("<br/>" becomes
    "<br></br>").

    If an element has an attribute test:sort="children", the attribute is
    removed and its immediate child nodes are sorted textually.  If the
    attribute value is test:sort="recursively", the sorting happens at
    all levels (unless specifically prohibited with test:sort="not").

    If recursively_sort is given, it is a sequence of tags that will have
    test:sort="recursively" automatically appended to their attribute lists in
    the text.  Use it when you cannot or do not want to modify the XML document
    itself.

    Caveats:
     - normalize_xml does not deal well with text nodes
     - normalize_xml does not help when different prefixes are used for the
       same namespace
     - normalize_xml does not handle all XML features (CDATA sections, inline
       DTDs, processing instructions, comments)
    """
    import libxml2 # XXX Creates a dependency on libxml2.
    import cgi

    class Document:

        def __init__(self):
            self.children = []
            self.sort_recursively = False

        def render(self, level=0):
            result = []
            for child in self.children:
                result.append(child.render(level))
            return ''.join(result)

    class Element:

        def __init__(self, parent, tag, attrlist, sort=False,
                     sort_recursively=False):
            self.parent = parent
            self.tag = tag
            self.attrlist = attrlist
            self.children = []
            self.sort = sort
            self.sort_recursively = sort_recursively

        def render(self, level):
            result = []
            indent = '  ' * level
            line = '%s<%s' % (indent, self.tag)
            for attr in self.attrlist:
                if len(line + attr) < 78:
                    line += attr
                else:
                    result.append(line)
                    result.append('\n')
                    line = '%s %s%s' % (indent, ' ' * len(self.tag), attr)
            if self.children:
                s = ''.join([child.render(level+1) for child in self.children])
            else:
                s = ''
            if s:
                result.append('%s>\n' % line)
                result.append(s)
                result.append('%s</%s>\n' % (indent, self.tag))
            else:
                result.append('%s/>\n' % line)
            return ''.join(result)

        def finalize(self):
            if self.sort:
                self.children.sort(lambda x, y: cmp(x.key, y.key))
            self.key = self.render(0)

    class Text:

        def __init__(self, data):
            self.data = data
            self.key = None

        def render(self, level):
            data = cgi.escape(self.data.strip())
            if data:
                indent = '  ' * level
                return ''.join(['%s%s\n' % (indent, line.strip())
                                for line in data.splitlines()])
            else:
                return ''

    class Handler:

        def __init__(self):
            self.level = 0
            self.result = []
            self.root = self.cur = Document()
            self.last_text = None

        def startElement(self, tag, attrs):
            sort = sort_recursively = self.cur.sort_recursively
            if attrs:
                if 'test:sort' in attrs:
                    value = attrs['test:sort']
                    del attrs['test:sort']
                    if value == 'children':
                        sort = True
                    elif value == 'recursively':
                        sort = sort_recursively = True
                    elif value == 'not':
                        sort = sort_recursively = False
                attrlist = attrs.items()
                attrlist.sort()
                attrlist = [' %s="%s"' % (k, cgi.escape(v, True))
                            for k, v in attrlist]
            else:
                attrlist = []
            child = Element(self.cur, tag, attrlist, sort=sort,
                            sort_recursively=sort_recursively)
            self.cur.children.append(child)
            self.cur = child
            self.last_text = None

        def endElement(self, tag):
            self.cur.finalize()
            self.cur = self.cur.parent
            self.last_text = None

        def characters(self, data):
            if self.last_text is not None:
                self.last_text.data += data
            else:
                self.last_text = Text(data)
                self.cur.children.append(self.last_text)

        def render(self):
            return self.root.render()

    for tag in recursively_sort:
        xml = xml.replace('<%s' % tag,
                          '<%s test:sort="recursively"' % tag)
    try:
        handler = Handler()
        ctx = libxml2.createPushParser(handler, "", 0, "")
        ret = ctx.parseChunk(xml, len(xml), True)
        if ret:
            return "PARSE ERROR: %r\n%s" % (ret, xml)
        return ''.join(handler.render())
    except libxml2.parserError, e:
        return "ERROR: %s" % e


class TestCalendarEventView(unittest.TestCase, XMLCompareMixin):
    # Legacy unit tests for CalendarEventView

    def setUp(self):
        setup.placelessSetUp()
        setup.setUpTraversal()

    def tearDown(self):
        setup.placelessTearDown()

    def createView(self, ev=None):
        from schoolbell.app.cal import Calendar
        from schoolbell.app.browser.cal import CalendarEventView
        if ev is None:
            ev = self.createOrdinaryEvent()
        view = CalendarEventView(ev, Calendar())
        return view

    def createOrdinaryEvent(self):
        ev = createEvent('2004-12-01 12:01', '1h', 'Main event',
                         unique_id="id!")
        return ev

    # TODO: test canEdit

    def test_cssClass(self):
        def class_of(event):
            return self.createView(event).cssClass()
        self.assertEquals(class_of(self.createOrdinaryEvent()), 'event')

    def test_duration(self):
        view = self.createView()
        view.request = TestRequest()
        self.assertEquals(view.duration(), '12:01&ndash;13:01')

        ev = createEvent('2004-12-01 12:01', '1d', 'Long event')
        view = self.createView(ev)
        view.request = TestRequest()
        self.assertEquals(view.duration(),
                          '2004-12-01 12:01&ndash;2004-12-02 12:01')

    def test_full(self):
        view = self.createView()
        view.canEdit = lambda: False
        request = TestRequest()
        content = view.full(request, date(2004, 12, 2))
        self.assertEqualsXML(content.replace('&ndash;', '--'), """
            <div class="calevent">
              <h3>
                Main event
              </h3>
              12:01--13:01
            </div>
            """)

        view.canEdit = lambda: True
        content = view.full(request, date(2004, 12, 2))
        self.assertEqualsXML(content.replace('&ndash;', '--'), """
            <div class="calevent">
              <div class="dellink">
                <a href="delete_event.html?date=2004-12-02&amp;event_id=id%21">
                  [delete]
                </a>
                <div>
                  Public
                </div>
              </div>
              <h3>
                <a href="edit_event.html?date=2004-12-02&amp;event_id=id%21">
                  Main event
                </a>
              </h3>
              12:01--13:01
            </div>
            """)

        ev = createEvent('2004-12-01 12:01', '1h', 'Main event',
                         unique_id="id", location="Office")
        view = self.createView(ev)
        view.canEdit = lambda: False
        content = view.full(request, date(2004, 12, 2))
        self.assertEqualsXML(content.replace('&ndash;', '--'), """
            <div class="calevent">
              <h3>
                Main event
              </h3>
              12:01--13:01
              (Office)
            </div>
            """)

        # TODO: Disabled because we do not have private events yet.
        ##ev = createEvent('2004-12-01 12:01', '1h', 'Main event',
        ##                 unique_id="id", location="Office",
        ##                 privacy="private")
        ##view = self.createView(ev)
        ##view.canView = lambda: False
        ##content = view.full(request, date(2004, 12, 2))
        ##self.assertEqualsXML(content.replace('&ndash;', '--'), """
        ##    <div class="calevent">
        ##      <h3>
        ##        Busy
        ##      </h3>
        ##      12:01--13:01
        ##    </div>
        ##    """)

    def test_short(self):
        request = TestRequest()
        view = self.createView()
        view.canView = lambda: True
        self.assertEquals(view.short(request),
                          'Main event (12:01&ndash;13:01)')

        ev = createEvent('2004-12-01 12:01', '1d', 'Long event')
        view = self.createView(ev)
        view.canView = lambda: True
        self.assertEquals(view.short(request),
                          'Long event (Dec&nbsp;01&ndash;Dec&nbsp;02)')

        view = self.createView()
        view.canView = lambda: False
        self.assertEquals(view.short(request),
                          'Busy (12:01&ndash;13:01)')

        ev = createEvent('2005-01-17 12:01', '1d', '12345678901234567890')
        view = self.createView(ev)
        view.canView = lambda: True
        self.assertEquals(view.short(request),
                '12345678901234567890 (Jan&nbsp;17&ndash;Jan&nbsp;18)')

    def test_editLink_and_deleteLink(self):
        ev = createEvent('2004-12-01 12:01', '1h', 'Repeating event',
                         unique_id="s@me=id")
        view = self.createView(ev)
        view.date = date(2004, 12, 2)
        params = 'date=2004-12-02&event_id=s%40me%3Did'
        self.assertEquals(view.deleteLink(), 'delete_event.html?' + params)
        self.assertEquals(view.editLink(), 'edit_event.html?' + params)


class TestDailyCalendarView(unittest.TestCase):

    def test_title(self):
        from schoolbell.app.browser.cal import DailyCalendarView
        from schoolbell.app.app import Person

        view = DailyCalendarView(Person().calendar, TestRequest())
        view.update()
        self.assertEquals(view.cursor, date.today())

        view.request = TestRequest(form={'date': '2005-01-06'})
        view.update()
        self.assertEquals(view.title(), "Thursday, 2005-01-06")
        view.request = TestRequest(form={'date': '2005-01-07'})
        view.update()
        self.assertEquals(view.title(), "Friday, 2005-01-07")

    def test_update(self):
        from schoolbell.app.browser.cal import DailyCalendarView
        from schoolbell.app.app import Person

        view = DailyCalendarView(Person().calendar, TestRequest())
        view.update()
        self.assertEquals(view.cursor, date.today())

        view.request = TestRequest(form={'date': '2004-08-18'})
        view.update()
        self.assertEquals(view.cursor, date(2004, 8, 18))

    def test__setRange(self):
        from schoolbell.app.browser.cal import DailyCalendarView
        from schoolbell.app.app import Person

        person = Person("Da Boss")
        cal = person.calendar
        view = DailyCalendarView(cal, TestRequest())
        view.cursor = date(2004, 8, 16)

        def do_test(events, expected):
            view.starthour, view.endhour = 8, 19
            view._setRange(events)
            self.assertEquals((view.starthour, view.endhour), expected)

        do_test([], (8, 19))

        events = [createEvent('2004-08-16 7:00', '1min', 'workout')]
        do_test(events, (7, 19))

        events = [createEvent('2004-08-15 8:00', '1d', "long workout")]
        do_test(events, (0, 19))

        events = [createEvent('2004-08-16 20:00', '30min', "late workout")]
        do_test(events, (8, 21))

        events = [createEvent('2004-08-16 20:00', '5h', "long late workout")]
        do_test(events, (8, 24))

    def test_dayEvents(self):
        from schoolbell.app.browser.cal import DailyCalendarView
        from schoolbell.app.app import Person

        ev1 = createEvent('2004-08-12 12:00', '2h', "ev1")
        ev2 = createEvent('2004-08-12 13:00', '2h', "ev2")
        ev3 = createEvent('2004-08-12 14:00', '2h', "ev3")
        ev4 = createEvent('2004-08-11 14:00', '3d', "ev4")
        cal = Person().calendar
        for e in [ev1, ev2, ev3, ev4]:
            cal.addEvent(e)
        view = DailyCalendarView(cal, TestRequest())
        view.request = TestRequest()
        result = view.dayEvents(date(2004, 8, 12))
        expected = [ev4, ev1, ev2, ev3]
        fmt = lambda x: '[%s]' % ', '.join([e.title for e in x])
        self.assertEquals(result, expected,
                          '%s != %s' % (fmt(result), fmt(expected)))

    def test_getColumns(self):
        from schoolbell.app.browser.cal import DailyCalendarView
        from schoolbell.app.app import Person, Calendar

        person = Person(title="Da Boss")
        cal = person.calendar
        view = DailyCalendarView(cal, TestRequest())
        view.request = TestRequest()
        view.cursor = date(2004, 8, 12)

        self.assertEquals(view.getColumns(), 1)

        cal.addEvent(createEvent('2004-08-12 12:00', '2h', "Meeting"))
        self.assertEquals(view.getColumns(), 1)

        #
        #  Three events:
        #
        #  12 +--+
        #  13 |Me|+--+    <--- overlap
        #  14 +--+|Lu|+--+
        #  15     +--+|An|
        #  16         +--+
        #
        #  Expected result: 2

        cal.addEvent(createEvent('2004-08-12 13:00', '2h', "Lunch"))
        cal.addEvent(createEvent('2004-08-12 14:00', '2h', "Another meeting"))
        self.assertEquals(view.getColumns(), 2)

        #
        #  Four events:
        #
        #  12 +--+
        #  13 |Me|+--+    +--+ <--- overlap
        #  14 +--+|Lu|+--+|Ca|
        #  15     +--+|An|+--+
        #  16         +--+
        #
        #  Expected result: 3

        cal.addEvent(createEvent('2004-08-12 13:00', '2h',
                                 "Call Mark during lunch"))
        self.assertEquals(view.getColumns(), 3)

        #
        #  Events that do not overlap in real life, but overlap in our view
        #
        #    +-------------+-------------+-------------+
        #    | 12:00-12:30 | 12:30-13:00 | 12:00-12:00 |
        #    +-------------+-------------+-------------+
        #
        #  Expected result: 3

        cal.clear()
        cal.addEvent(createEvent('2004-08-12 12:00', '30min', "a"))
        cal.addEvent(createEvent('2004-08-12 12:30', '30min', "b"))
        cal.addEvent(createEvent('2004-08-12 12:00', '0min', "c"))
        self.assertEquals(view.getColumns(), 3)

    def test_getColumns_periods(self):
        from schoolbell.app.browser.cal import DailyCalendarView
        from schoolbell.app.app import Person, Calendar
        from schoolbell.calendar.utils import parse_datetime

        person = Person(title="Da Boss")
        cal = person.calendar
        view = DailyCalendarView(cal, TestRequest())
        view.cursor = date(2004, 8, 12)
        view.calendarRows = lambda: iter([
            ("B", parse_datetime('2004-08-12 10:00:00'), timedelta(hours=3)),
            ("C", parse_datetime('2004-08-12 13:00:00'), timedelta(hours=2)),
             ])
        cal.addEvent(createEvent('2004-08-12 09:00', '2h', "Whatever"))
        cal.addEvent(createEvent('2004-08-12 11:00', '2m', "Phone call"))
        cal.addEvent(createEvent('2004-08-12 11:10', '2m', "Phone call"))
        cal.addEvent(createEvent('2004-08-12 12:00', '2m', "Phone call"))
        cal.addEvent(createEvent('2004-08-12 12:30', '3h', "Nap"))
        self.assertEquals(view.getColumns(), 5)

    def test_getHours(self):
        from schoolbell.app.browser.cal import DailyCalendarView
        from schoolbell.app.app import Person

        person = Person(title="Da Boss")
        cal = person.calendar
        view = DailyCalendarView(cal, TestRequest())
        view.cursor = date(2004, 8, 12)
        view.starthour = 10
        view.endhour = 16
        result = list(view.getHours())
        self.assertEquals(result,
                          [{'duration': 60, 'time': '10:00',
                            'title': '10:00', 'cols': (None,)},
                           {'duration': 60, 'time': '11:00',
                            'title': '11:00', 'cols': (None,)},
                           {'duration': 60, 'time': '12:00',
                            'title': '12:00', 'cols': (None,)},
                           {'duration': 60, 'time': '13:00',
                            'title': '13:00', 'cols': (None,)},
                           {'duration': 60, 'time': '14:00',
                            'title': '14:00', 'cols': (None,)},
                           {'duration': 60, 'time': '15:00',
                            'title': '15:00', 'cols': (None,)},])

        ev1 = createEvent('2004-08-12 12:00', '2h', "Meeting")
        cal.addEvent(ev1)
        result = list(view.getHours())

        def clearTimeAndDuration(l):
            for d in l:
                del d['time']
                del d['duration']
            return l

        result = clearTimeAndDuration(result)
        self.assertEquals(result,
                          [{'title': '10:00', 'cols': (None,)},
                           {'title': '11:00', 'cols': (None,)},
                           {'title': '12:00', 'cols': (ev1,)},
                           {'title': '13:00', 'cols': ('',)},
                           {'title': '14:00', 'cols': (None,)},
                           {'title': '15:00', 'cols': (None,)}])

        #
        #  12 +--+
        #  13 |Me|+--+
        #  14 +--+|Lu|
        #  15 |An|+--+
        #  16 +--+
        #

        ev2 = createEvent('2004-08-12 13:00', '2h', "Lunch")
        ev3 = createEvent('2004-08-12 14:00', '2h', "Another meeting")
        cal.addEvent(ev2)
        cal.addEvent(ev3)

        result = list(view.getHours())
        self.assertEquals(clearTimeAndDuration(result),
                          [{'title': '10:00', 'cols': (None, None)},
                           {'title': '11:00', 'cols': (None, None)},
                           {'title': '12:00', 'cols': (ev1, None)},
                           {'title': '13:00', 'cols': ('', ev2)},
                           {'title': '14:00', 'cols': (ev3, '')},
                           {'title': '15:00', 'cols': ('', None)},])

        ev4 = createEvent('2004-08-11 14:00', '3d', "Visit")
        cal.addEvent(ev4)

        result = list(view.getHours())
        self.assertEquals(clearTimeAndDuration(result),
                          [{'title': '0:00', 'cols': (ev4, None, None)},
                           {'title': '1:00', 'cols': ('', None, None)},
                           {'title': '2:00', 'cols': ('', None, None)},
                           {'title': '3:00', 'cols': ('', None, None)},
                           {'title': '4:00', 'cols': ('', None, None)},
                           {'title': '5:00', 'cols': ('', None, None)},
                           {'title': '6:00', 'cols': ('', None, None)},
                           {'title': '7:00', 'cols': ('', None, None)},
                           {'title': '8:00', 'cols': ('', None, None)},
                           {'title': '9:00', 'cols': ('', None, None)},
                           {'title': '10:00', 'cols': ('', None, None)},
                           {'title': '11:00', 'cols': ('', None, None)},
                           {'title': '12:00', 'cols': ('', ev1, None)},
                           {'title': '13:00', 'cols': ('', '', ev2)},
                           {'title': '14:00', 'cols': ('', ev3, '')},
                           {'title': '15:00', 'cols': ('', '', None)},
                           {'title': '16:00', 'cols': ('', None, None)},
                           {'title': '17:00', 'cols': ('', None, None)},
                           {'title': '18:00', 'cols': ('', None, None)},
                           {'title': '19:00', 'cols': ('', None, None)},
                           {'title': '20:00', 'cols': ('', None, None)},
                           {'title': '21:00', 'cols': ('', None, None)},
                           {'title': '22:00', 'cols': ('', None, None)},
                           {'title': '23:00', 'cols': ('', None, None)}])

    def test_rowspan(self):
        from schoolbell.app.browser.cal import DailyCalendarView
        from schoolbell.app.app import Person
        view = DailyCalendarView(None, TestRequest())
        view.starthour = 10
        view.endhour = 18
        view.cursor = date(2004, 8, 12)
        view.request = TestRequest()

        self.assertEquals(view.rowspan(
                            createEvent('2004-08-12 12:00', '1d', "Long")), 6)
        self.assertEquals(view.rowspan(
                            createEvent('2004-08-11 12:00', '3d', "Very")), 8)
        self.assertEquals(view.rowspan(
                            createEvent('2004-08-12 12:00', '10min', "")), 1)
        self.assertEquals(view.rowspan(
                            createEvent('2004-08-12 12:00', '1h+1sec', "")), 2)
        self.assertEquals(view.rowspan(
                            createEvent('2004-08-12 09:00', '3h', "")), 2)

    def test_rowspan_periods(self):
        from schoolbell.app.browser.cal import DailyCalendarView
        from schoolbell.app.app import Person
        from schoolbell.calendar.utils import parse_datetime
        view = DailyCalendarView(None, TestRequest())
        view.calendarRows = lambda: iter([
            ("8", parse_datetime('2004-08-12 08:00:00'), timedelta(hours=1)),
            ("A", parse_datetime('2004-08-12 09:00:00'), timedelta(hours=1)),
            ("B", parse_datetime('2004-08-12 10:00:00'), timedelta(hours=3)),
            ("C", parse_datetime('2004-08-12 13:00:00'), timedelta(hours=2)),
            ("D", parse_datetime('2004-08-12 15:00:00'), timedelta(hours=1)),
            ("16", parse_datetime('2004-08-12 16:00:00'), timedelta(hours=1)),
            ("17", parse_datetime('2004-08-12 17:00:00'), timedelta(hours=1)),
             ])
        view.cursor = date(2004, 8, 12)
        view.starthour = 8
        view.endhour = 18

        self.assertEquals(view.rowspan(
                            createEvent('2004-08-12 12:00', '1d', "Long")), 5)
        self.assertEquals(view.rowspan(
                            createEvent('2004-08-11 12:00', '3d', "Very")), 7)
        self.assertEquals(view.rowspan(
                            createEvent('2004-08-12 12:00', '10min', "")), 1)
        self.assertEquals(view.rowspan(
                            createEvent('2004-08-12 12:00', '1h+1sec', "")), 2)
        self.assertEquals(view.rowspan(
                            createEvent('2004-08-12 13:00', '2h', "")), 1)
        self.assertEquals(view.rowspan(
                            createEvent('2004-08-12 09:00', '3h', "")), 2)

    def test_eventTop(self):
        from schoolbell.app.browser.cal import DailyCalendarView
        view = DailyCalendarView(None, TestRequest())
        view.starthour = 8
        view.endhour = 18
        view.cursor = date(2004, 8, 12)
        view.request = TestRequest()

        self.assertEquals(view.eventTop(
                            createEvent('2004-08-12 09:00', '1h', "")), 4)
        self.assertEquals(view.eventTop(
                            createEvent('2004-08-12 10:00', '1h', "")), 8)
        self.assertEquals(view.eventTop(
                            createEvent('2004-08-12 10:15', '1h', "")), 9)
        self.assertEquals(view.eventTop(
                            createEvent('2004-08-12 10:30', '1h', "")), 10)
        self.assertEquals(view.eventTop(
                            createEvent('2004-08-12 10:45', '1h', "")), 11)

    def test_eventHeight(self):
        from schoolbell.app.browser.cal import DailyCalendarView
        view = DailyCalendarView(None, TestRequest())
        view.starthour = 8
        view.endhour = 18
        view.cursor = date(2004, 8, 12)
        view.request = TestRequest()

        self.assertEquals(view.eventHeight(
                            createEvent('2004-08-12 09:00', '0', "")), 1)
        self.assertEquals(view.eventHeight(
                            createEvent('2004-08-12 09:00', '14m', "")), 1)
        self.assertEquals(view.eventHeight(
                            createEvent('2004-08-12 09:00', '1h', "")), 4)
        self.assertEquals(view.eventHeight(
                            createEvent('2004-08-12 10:00', '2h', "")), 8)
        self.assertEquals(view.eventHeight(
                            createEvent('2004-08-12 10:00', '2h+15m', "")), 9)
        self.assertEquals(view.eventHeight(
                            createEvent('2004-08-12 10:00', '2h+30m', "")), 10)
        self.assertEquals(view.eventHeight(
                            createEvent('2004-08-12 10:00', '2h+45m', "")), 11)

    def test_do_POST(self):
        return # XXX TODO
        from schoolbell.app.browser.cal import DailyCalendarView
        from schooltool.cal import ACLCalendar
        from schooltool.model import Person, Group
        from schooltool.component import getRelatedObjects
        from schooltool.uris import URICalendarProvider

        from schooltool import relationship
        relationship.setUp()

        context = self.manager.calendar
        view = DailyCalendarView(context)

        view.request = RequestStub(authenticated_user=self.manager,
                args={'overlay':['/groups/locations','/groups/managers'],
                    'OVERLAY': ''})

        view.do_POST(view.request)

        related = getRelatedObjects(self.manager, URICalendarProvider)
        self.assertEquals(related, [self.locations, self.managers])


def doctest_CalendarViewBase():
    """Tests for CalendarViewBase.

        >>> from schoolbell.app.browser.cal import CalendarViewBase

        >>> from schoolbell.app.app import Calendar
        >>> calendar = Calendar()
        >>> directlyProvides(calendar, IContainmentRoot)

    CalendarViewBase has a method calURL used for forming links to other
    calendar views on other dates.

        >>> request = TestRequest()
        >>> view = CalendarViewBase(calendar, request)
        >>> view.cursor = date(2005, 2, 3)

        >>> view.calURL("quarterly")
        'http://127.0.0.1/calendar/quarterly.html?date=2005-02-03'
        >>> view.calURL("quarterly", date(2005, 12, 13))
        'http://127.0.0.1/calendar/quarterly.html?date=2005-12-13'

    update() sets the cursor for the view.  If it does not find a date in
    request, it defaults to the current day:

        >>> view.update()
        >>> view.cursor == date.today()
        True

    The date can be provided in the request:

        >>> request.form['date'] = '2005-01-02'
        >>> view.update()

        >>> view.cursor
        datetime.date(2005, 1, 2)

    Some convenience methods are available for getting info from
    the view of an individual event:

        >>> event = createEvent('2005-02-04 16:42', '15min', 'Coding session')
        >>> view.eventClass(event)
        'event'
        >>> view.renderEvent(event, date(2005, 2, 4)) # doctest: +ELLIPSIS
        u'<div class="calevent">...Coding session...

        >>> view.eventShort(event)
        'Coding session (16:42&ndash;16:57)'

        >>> view.eventHidden(event)
        False

    """


def doctest_DailyCalendarView():
    r"""Tests for DailyCalendarView.

        >>> from schoolbell.app.browser.cal import DailyCalendarView

        >>> from schoolbell.app.app import Calendar
        >>> calendar = Calendar()
        >>> directlyProvides(calendar, IContainmentRoot)
        >>> view = DailyCalendarView(calendar, TestRequest())

    prev() and next() return links for adjacent weeks:

        >>> view.cursor = date(2004, 8, 18)
        >>> view.prev()
        'http://127.0.0.1/calendar/daily.html?date=2004-08-17'
        >>> view.next()
        'http://127.0.0.1/calendar/daily.html?date=2004-08-19'

    """


def doctest_WeeklyCalendarView():
    """Tests for WeeklyCalendarView.

        >>> from schoolbell.app.browser.cal import WeeklyCalendarView

        >>> from schoolbell.app.app import Calendar
        >>> calendar = Calendar()
        >>> directlyProvides(calendar, IContainmentRoot)
        >>> view = WeeklyCalendarView(calendar, TestRequest())

    title() forms a nice title for the calendar:

        >>> view.cursor = date(2005, 2, 3)
        >>> view.title()
        u'February, 2005 (week 5)'

    prev() and next() return links for adjacent weeks:

        >>> view.cursor = date(2004, 8, 18)
        >>> view.prev()
        'http://127.0.0.1/calendar/weekly.html?date=2004-08-11'
        >>> view.next()
        'http://127.0.0.1/calendar/weekly.html?date=2004-08-25'

    getCurrentWeek is a shortcut for view.getWeek(view.cursor)

        >>> view.cursor = "works"
        >>> view.getWeek = lambda x: "really " + x
        >>> view.getCurrentWeek()
        'really works'

    """


def doctest_MonthlyCalendarView():
    """Tests for MonthlyCalendarView.

        >>> from schoolbell.app.browser.cal import MonthlyCalendarView

        >>> from schoolbell.app.app import Calendar
        >>> calendar = Calendar()
        >>> directlyProvides(calendar, IContainmentRoot)
        >>> view = MonthlyCalendarView(calendar, TestRequest())

    title() forms a nice title for the calendar:

        >>> view.cursor = date(2005, 2, 3)
        >>> view.title()
        u'February, 2005'

    Some helpers for are provided for use in the template:

        >>> view.dayOfWeek(date(2005, 5, 17))
        u'Tuesday'

        >>> view.weekTitle(date(2005, 5, 17))
        u'Week 20'

    prev() and next() return links for adjacent months:

        >>> view.cursor = date(2004, 8, 18)
        >>> view.prev()
        'http://127.0.0.1/calendar/monthly.html?date=2004-07-01'
        >>> view.next()
        'http://127.0.0.1/calendar/monthly.html?date=2004-09-01'

    getCurrentWeek is a shortcut for view.getMonth(view.cursor)

        >>> view.cursor = "works"
        >>> view.getMonth = lambda x: "really " + x
        >>> view.getCurrentMonth()
        'really works'

    """


def doctest_YearlyCalendarView():
    r"""Tests for YearlyCalendarView.

        >>> from schoolbell.app.browser.cal import YearlyCalendarView

        >>> from schoolbell.app.app import Calendar
        >>> calendar = Calendar()
        >>> directlyProvides(calendar, IContainmentRoot)
        >>> view = YearlyCalendarView(calendar, TestRequest())

    monthTitle() returns names of months:

        >>> view.monthTitle(date(2005, 2, 3))
        u'February'
        >>> view.monthTitle(date(2005, 8, 3))
        u'August'

    dayOfWeek() returns short names of weekdays:

        >>> view.shortDayOfWeek(date(2005, 2, 3))
        u'Thu'
        >>> view.shortDayOfWeek(date(2005, 8, 3))
        u'Wed'

    prev() and next() return links for adjacent years:

        >>> view.cursor = date(2004, 8, 18)
        >>> view.prev()
        'http://127.0.0.1/calendar/yearly.html?date=2003-01-01'
        >>> view.next()
        'http://127.0.0.1/calendar/yearly.html?date=2005-01-01'

    renderRow() renders HTML for one week of events.  It is implemented
    in python for performance reasons.

        >>> week = view.getWeek(date(2004, 2, 4))[2:4]
        >>> print view.renderRow(week, 2)
        <td class="cal_yearly_day">
        <a href="http://127.0.0.1/calendar/daily.html?date=2004-02-04" class="cal_yearly_day">4</a>
        </td>
        <td class="cal_yearly_day">
        <a href="http://127.0.0.1/calendar/daily.html?date=2004-02-05" class="cal_yearly_day">5</a>
        </td>

    """


def setUp(test):
    setup.placelessSetUp()
    setup.setUpTraversal()


def tearDown(test):
    setup.placelessTearDown()


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestCalendarViewBase))
    suite.addTest(unittest.makeSuite(TestCalendarEventView))
    suite.addTest(unittest.makeSuite(TestDailyCalendarView))
    suite.addTest(doctest.DocTestSuite(setUp=setUp, tearDown=tearDown))
    suite.addTest(doctest.DocTestSuite('schoolbell.app.browser.cal'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
