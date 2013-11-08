#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003 Shuttleworth Foundation
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
Things common to the SchoolTool server and clients.
"""

import re
import locale
import datetime
import urllib
import HTMLParser

import zope.interface
import zope.component
from zope.publisher.interfaces import IApplicationRequest
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.security.management import queryInteraction
from zope.schema import Date
from zope.traversing.browser.absoluteurl import absoluteURL
from zope.interface import Interface, implements

__metaclass__ = type


def parse_date(value):
    """Parse a ISO-8601 YYYY-MM-DD date value.

    Examples:

        >>> parse_date('2003-09-01')
        datetime.date(2003, 9, 1)
        >>> parse_date('20030901')
        Traceback (most recent call last):
          ...
        ValueError: Invalid date: '20030901'
        >>> parse_date('2003-IX-01')
        Traceback (most recent call last):
          ...
        ValueError: Invalid date: '2003-IX-01'
        >>> parse_date('2003-09-31')
        Traceback (most recent call last):
          ...
        ValueError: Invalid date: '2003-09-31'
        >>> parse_date('2003-09-30-15-42')
        Traceback (most recent call last):
          ...
        ValueError: Invalid date: '2003-09-30-15-42'

    """
    try:
        y, m, d = map(int, value.split('-'))
        return datetime.date(y, m, d)
    except ValueError:
        raise ValueError("Invalid date: %r" % value)


def parse_time(value):
    """Parse a ISO 8601 HH:MM time value.

    Examples:

        >>> parse_time('01:25')
        datetime.time(1, 25)
        >>> parse_time('9:15')
        datetime.time(9, 15)
        >>> parse_time('12:1')
        datetime.time(12, 1)
        >>> parse_time('00:00')
        datetime.time(0, 0)
        >>> parse_time('23:59')
        datetime.time(23, 59)
        >>> parse_time('24:00')
        Traceback (most recent call last):
          ...
        ValueError: Invalid time: '24:00'
        >>> parse_time('06:30PM')
        Traceback (most recent call last):
          ...
        ValueError: Invalid time: '06:30PM'

    """
    try:
        h, m = map(int, value.split(':'))
        return datetime.time(h, m)
    except ValueError:
        raise ValueError("Invalid time: %r" % value)


def parse_time_range(value, default_duration=None):
    """Parse a range of times (e.g. 9:45-14:20).

    This is an alternative implementation of time span parsing, taken from
    schooltool timetabling package.

    Example:

        >>> parse_time_range('9:45-14:20')
        (datetime.time(9, 45), datetime.timedelta(0, 16500))

        >>> parse_time_range('00:00-24:00')
        (datetime.time(0, 0), datetime.timedelta(1))

        >>> parse_time_range('10:00-10:00')
        (datetime.time(10, 0), datetime.timedelta(0))

    Time ranges may span midnight

        >>> parse_time_range('23:00-02:00')
        (datetime.time(23, 0), datetime.timedelta(0, 10800))

    When the default duration is specified, you may omit the second time

        >>> parse_time_range('23:00', 45)
        (datetime.time(23, 0), datetime.timedelta(0, 2700))

    Invalid values cause a ValueError

        >>> parse_time_range('something else')
        Traceback (most recent call last):
          ...
        ValueError: bad time range: something else

        >>> parse_time_range('9:00')
        Traceback (most recent call last):
          ...
        ValueError: duration is not specified

        >>> parse_time_range('9:00-9:75')
        Traceback (most recent call last):
          ...
        ValueError: minute must be in 0..59

        >>> parse_time_range('5:99-6:00')
        Traceback (most recent call last):
          ...
        ValueError: minute must be in 0..59

        >>> parse_time_range('14:00-24:01')
        Traceback (most recent call last):
          ...
        ValueError: hour must be in 0..23

    White space can be inserted between times

        >>> parse_time_range(' 9:45 - 14:20 ')
        (datetime.time(9, 45), datetime.timedelta(0, 16500))

    but not inside times

        >>> parse_time_range('9: 45-14:20')
        Traceback (most recent call last):
          ...
        ValueError: bad time range: 9: 45-14:20

    """
    m = re.match(r'\s*(\d+):(\d+)\s*(?:-\s*(\d+):(\d+)\s*)?$', value)
    if not m:
        raise ValueError('bad time range: %s' % value)
    h1, m1 = int(m.group(1)), int(m.group(2))
    if not m.group(3):
        if default_duration is None:
            raise ValueError('duration is not specified')
        duration = default_duration
    else:
        h2, m2 = int(m.group(3)), int(m.group(4))
        if (h2, m2) != (24, 0):   # 24:00 is expressly allowed here
            datetime.time(h2, m2) # validate the second time
        duration = (h2*60+m2) - (h1*60+m1)
        if duration < 0:
            duration += 1440
    return datetime.time(h1, m1), datetime.timedelta(minutes=duration)


def format_time_range(start, duration):
    """Format a range of times (e.g. 9:45-14:20).

    This is an alternative implementation of time span formatting, taken from
    schooltool timetabling package.

    Example:

        >>> format_time_range(datetime.time(9, 45),
        ...                   datetime.timedelta(0, 16500))
        '09:45-14:20'

        >>> format_time_range(datetime.time(0, 0), datetime.timedelta(1))
        '00:00-24:00'

        >>> format_time_range(datetime.time(10, 0), datetime.timedelta(0))
        '10:00-10:00'

        >>> format_time_range(datetime.time(23, 0),
        ...                   datetime.timedelta(0, 10800))
        '23:00-02:00'

    """
    end = (datetime.datetime.combine(datetime.date.today(), start) + duration)
    ends = end.strftime('%H:%M')
    if ends == '00:00' and duration == datetime.timedelta(1):
        return '00:00-24:00' # special case
    else:
        return '%s-%s' % (start.strftime('%H:%M'), ends)



def parse_datetime(s):
    """Parse a ISO 8601 date/time value.

    Only a small subset of ISO 8601 is accepted:

      YYYY-MM-DD HH:MM:SS
      YYYY-MM-DD HH:MM:SS.ssssss
      YYYY-MM-DDTHH:MM:SS
      YYYY-MM-DDTHH:MM:SS.ssssss

    Returns a datetime.datetime object without a time zone.

    Examples:

        >>> parse_datetime('2003-04-05 11:22:33.456789')
        datetime.datetime(2003, 4, 5, 11, 22, 33, 456789)

        >>> parse_datetime('2003-04-05 11:22:33.456')
        datetime.datetime(2003, 4, 5, 11, 22, 33, 456000)

        >>> parse_datetime('2003-04-05 11:22:33.45678999')
        datetime.datetime(2003, 4, 5, 11, 22, 33, 456789)

        >>> parse_datetime('01/02/03')
        Traceback (most recent call last):
          ...
        ValueError: Bad datetime: 01/02/03

    """
    m = re.match(r"(\d+)-(\d+)-(\d+)[ T](\d+):(\d+):(\d+)([.](\d+))?$", s)
    if not m:
        raise ValueError("Bad datetime: %s" % s)
    ssssss = m.groups()[7]
    if ssssss:
        ssssss = int((ssssss + "00000")[:6])
    else:
        ssssss = 0
    y, m, d, hh, mm, ss = map(int, m.groups()[:6])
    return datetime.datetime(y, m, d, hh, mm, ss, ssssss)


locale_charset = locale.getpreferredencoding()


def to_locale(us):
    r"""Convert a Unicode string to the current locale encoding.

    Example:

        >>> from schooltool import common
        >>> old_locale_charset = common.locale_charset

        >>> common.locale_charset = 'UTF-8'
        >>> to_locale(u'\u263B')
        '\xe2\x98\xbb'

        >>> common.locale_charset = 'ASCII'
        >>> to_locale(u'Unrepresentable: \u263B')
        'Unrepresentable: ?'

        >>> locale_charset = old_locale_charset

    """
    return us.encode(locale_charset, 'replace')


def from_locale(s):
    r"""Convert an 8-bit string in locale encoding to Unicode.

    Example:

        >>> from schooltool import common
        >>> old_locale_charset = common.locale_charset

        >>> from_locale('xyzzy')
        u'xyzzy'

        >>> common.locale_charset = 'UTF-8'
        >>> from_locale('\xe2\x98\xbb')
        u'\u263b'

        >>> locale_charset = old_locale_charset

    """
    return unicode(s, locale_charset)


def looks_like_a_uri(uri):
    r"""Check if the argument looks like a URI string.

    Refer to http://www.ietf.org/rfc/rfc2396.txt for details.
    We're only approximating to the spec.

    Some examples of valid URI strings:

        >>> looks_like_a_uri('http://foo/bar?baz#quux')
        True
        >>> looks_like_a_uri('HTTP://foo/bar?baz#quux')
        True
        >>> looks_like_a_uri('mailto:root')
        True

    These strings are all invalid URIs:

        >>> looks_like_a_uri('2HTTP://foo/bar?baz#quux')
        False
        >>> looks_like_a_uri('\nHTTP://foo/bar?baz#quux')
        False
        >>> looks_like_a_uri('mailto:postmaster ')
        False
        >>> looks_like_a_uri('mailto:postmaster text')
        False
        >>> looks_like_a_uri('nocolon')
        False
        >>> looks_like_a_uri(None)
        False

    """
    uri_re = re.compile(r"^[A-Za-z][A-Za-z0-9+-.]*:\S\S*$")
    return bool(uri and uri_re.match(uri) is not None)


def unquote_uri(uri):
    r"""Unquote a URI.

       >>> unquote_uri('/terms/%C5%BEiema')
       u'/terms/\u017eiema'

       >>> unquote_uri(u'/terms/%C5%BEiema')
       u'/terms/\u017eiema'

    """
    return urllib.unquote(str(uri)).decode('UTF-8')


def collect(fn):
    """Convert a generator to a function that returns a list of items.

        >>> @collect
        ... def something(x, y, z):
        ...     yield x
        ...     yield y + z

        >>> something(1, 2, 3)
        [1, 5]

    """
    def collector(*args, **kw):
        return list(fn(*args, **kw))
    collector.__name__ = fn.__name__
    collector.__doc__ = fn.__doc__
    collector.__dict__ = fn.__dict__
    collector.__module__ = fn.__module__
    return collector


class IDateRange(Interface):
    """A range of dates (inclusive).

    If r is an IDateRange, then the following invariant holds:
    r.first <= r.last

    Note that empty date ranges cannot be represented.
    """

    first = Date(
        title=u"The first day of the period of time covered.")

    last = Date(
        title=u"The last day of the period covered.")

    def __iter__():
        """Iterate over all dates in the range from the first to the last."""

    def __contains__(date):
        """Return True if the date is within the range, otherwise False.

        Raises a TypeError if date is not a datetime.date.
        """

    def __len__():
        """Return the number of dates covered by the range."""

    def overlaps(date_range):
        """Return whether this daterange overlaps with the other daterange."""

    def intersection(other_range):
        """Return intersection of date ranges (or None)."""



class DateRange(object):
    """A date range implementation using the standard datetime module.

    Date ranges are low-level components that represent a date
    span. They are mainly used to implement the date handling in
    terms:

      >>> january = DateRange(datetime.date(2003, 1, 1), datetime.date(2003, 1, 31))
      >>> IDateRange.providedBy(january)
      True

    You can use date ranges to check whether a certain date is within
    the range:

      >>> datetime.date(2002, 12, 31) in january
      False
      >>> datetime.date(2003, 2, 1) in january
      False
      >>> datetime.date(2003, 1, 1) in january
      True
      >>> datetime.date(2003, 1, 12) in january
      True
      >>> datetime.date(2003, 1, 31) in january
      True

    You can ask the date range for the amount of dates it includes.

      >>> days = list(january)
      >>> len(days)
      31
      >>> len(january)
      31

    As you can see, the boundary dates are inclusive. You can also
    iterate through all the dates in the date range.

      >>> days = DateRange(
      ...     datetime.date(2003, 1, 1), datetime.date(2003, 1, 2))
      >>> list(days)
      [datetime.date(2003, 1, 1), datetime.date(2003, 1, 2)]

      >>> days = DateRange(
      ...     datetime.date(2003, 1, 1), datetime.date(2003, 1, 1))
      >>> list(days)
      [datetime.date(2003, 1, 1)]

    If the beginning of the of the date range is later than the end, a
    value error is raised:

      >>> DateRange(datetime.date(2003, 1, 2),
      ...           datetime.date(2003, 1, 1)) # doctest: +NORMALIZE_WHITESPACE
      Traceback (most recent call last):
      ...
      ValueError: Last date datetime.date(2003, 1, 1) less than
                  first date datetime.date(2003, 1, 2)

    """
    implements(IDateRange)

    def __init__(self, first, last):
        self.first = first
        self.last = last
        if last < first:
            raise ValueError("Last date %r less than first date %r" %
                             (last, first))

    def __iter__(self):
        date = self.first
        while date <= self.last:
            yield date
            date += datetime.date.resolution

    def __len__(self):
        return (self.last - self.first).days + 1

    def __contains__(self, date):
        return self.first <= date <= self.last

    def overlaps(self, date_range):
        """Return whether this daterange overlaps with the other daterange.

           >>> from datetime import timedelta as td
           >>> def parse_inverval(interval):
           ...     first_date = datetime.date(2005, 1, 1)
           ...     start = len(interval) - len(interval.lstrip())
           ...     length = len(interval.strip())
           ...     end = start + length - 1
           ...     return DateRange(first_date + td(days=start),
           ...                      first_date + td(days=end))

           >>> interval = parse_inverval(' [===]  ')
           >>> print interval.first, interval.last
           2005-01-02 2005-01-06

           >>> interval = parse_inverval('  [===]   ')
           >>> print interval.first, interval.last
           2005-01-03 2005-01-07

           >>> def overlap(interval1, interval2):
           ...     i1 = parse_inverval(interval1)
           ...     i2 = parse_inverval(interval2)
           ...     return i1.overlaps(i2)

           >>> overlap(' [===]                     ',
           ...         '       [===========]       ')
           False

           >>> overlap(' [====]                    ',
           ...         '       [===========]       ')
           False

           >>> overlap(' [=====]                   ',
           ...         '       [===========]       ')
           True

           >>> overlap(' [=======]                 ',
           ...         '       [===========]       ')
           True

           >>> overlap('       [===========]       ',
           ...         '       [===========]       ')
           True

           >>> overlap('        [=========]        ',
           ...         '       [===========]       ')
           True

           >>> overlap('                [========] ',
           ...         '       [===========]       ')
           True

           >>> overlap('                   [=====] ',
           ...         '       [===========]       ')
           True

           >>> overlap('                    [====] ',
           ...         '       [===========]       ')
           False

           >>> overlap('                     [===] ',
           ...         '       [===========]       ')
           False

           >>> overlap('     [===============]     ',
           ...         '       [===========]       ')
           True

        """
        return self.last >= date_range.first and self.first <= date_range.last

    def intersection(self, other_range):
        """Return whether this daterange overlaps with the other daterange.

           >>> dr = DateRange(datetime.date(2005, 2, 10),
           ...                datetime.date(2005, 2, 15))

           >>> dr_before = DateRange(datetime.date(2005, 2, 1),
           ...                       datetime.date(2005, 2, 9))

           >>> print dr.intersection(dr_before)
           None

           >>> dr_after = DateRange(datetime.date(2005, 2, 16),
           ...                      datetime.date(2005, 2, 19))

           >>> print dr.intersection(dr_after)
           None

           >>> intersection = dr.intersection(DateRange(
           ...     datetime.date(2005, 2, 1), datetime.date(2005, 2, 10)))
           >>> print intersection.first, intersection.last
           2005-02-10 2005-02-10

           >>> intersection = dr.intersection(DateRange(
           ...     datetime.date(2005, 2, 13), datetime.date(2005, 2, 25)))
           >>> print intersection.first, intersection.last
           2005-02-13 2005-02-15

           >>> intersection = dr.intersection(DateRange(
           ...     datetime.date(2005, 2, 15), datetime.date(2005, 2, 25)))
           >>> print intersection.first, intersection.last
           2005-02-15 2005-02-15

           >>> intersection = dr.intersection(DateRange(
           ...     datetime.date(2005, 2, 13), datetime.date(2005, 2, 14)))
           >>> print intersection.first, intersection.last
           2005-02-13 2005-02-14

        """
        if (other_range.last < self.first or
            other_range.first > self.last):
            return None
        return DateRange(max(self.first, other_range.first),
                         min(self.last, other_range.last))


_version = None

def get_version():
    global _version
    if _version is not None:
        return _version
    import pkg_resources
    _version = pkg_resources.get_distribution('schooltool').version
    return _version


def get_all_versions():
    import pkg_resources
    versions = []
    versions.append(pkg_resources.get_distribution('schooltool'))
    for entry in pkg_resources.iter_entry_points('z3c.autoinclude.plugin'):
        if (entry.name == 'target' and
            entry.module_name == 'schooltool'):
            versions.append(entry.dist)
    for entry in pkg_resources.iter_entry_points('schooltool.plugin_configuration'):
        if entry.dist not in versions:
            versions.append(entry.dist)
    return sorted(versions, key=lambda dist: dist.project_name)


def getRequestFromInteraction(request_type=IApplicationRequest):
    """Extract the browser request from the current interaction.

    Returns None when there is no interaction, or when the interaction has no
    participations that provide request_type.
    """
    interaction = queryInteraction()
    if interaction is not None:
        for participation in interaction.participations:
            if request_type.providedBy(participation):
                return participation
    return None


from zope.i18nmessageid import Message, MessageFactory
SchoolToolMessage = MessageFactory("schooltool")

def format_message(message, mapping=None):
    """Add mapping to a zope.i18nmessageid.Message."""
    assert isinstance(message, Message)
    return message.__class__(message, mapping=mapping)


def stupid_form_key(item):
    """Simple form key that uses item's __name__.
    Very unsafe: __name__ is expected to be a unicode string that contains
    who knows what.
    """
    return item.__name__


def simple_form_key(item):
    """Unique form key for items contained within a single container."""
    name = getattr(item, '__name__', None)
    if name is None:
        return None
    key = unicode(name).encode('punycode')
    key = urllib.quote(key)
    return key


class IResourceURIGetter(zope.interface.Interface):

    def __call__(library_name, resource_name):
        """Return resource from the library."""


def getResourceURL(library_name, resource_name, request):
    getter = zope.component.queryAdapter(
        request, IResourceURIGetter,
        name=library_name, default=None)
    if getter is None:
        getter = zope.component.queryAdapter(
            request, IResourceURIGetter,
            default=None)
    if getter is None:
        return None
    resource = getter(library_name, resource_name)
    return resource


class CommonResourceURL(object):
    zope.component.adapts(IBrowserRequest)
    zope.interface.implements(IResourceURIGetter)

    def __init__(self, request):
        self.request = request

    def __call__(self, library_name, resource_name):
        if not resource_name:
            return None
        if library_name is not None:
            library = zope.component.queryAdapter(self.request, name=library_name)
            resource = library.get(resource_name)
        else:
            resource = zope.component.queryAdapter(self.request, name=resource_name)
        if resource is None:
            return None
        return absoluteURL(resource, self.request)


def data_uri(payload, mime=None):
    payload = payload.encode('base64').replace('\n','')
    result = 'data:'
    if mime:
        result += mime + ';'
    result = result + 'base64,' + payload
    return result


class HTMLToText(HTMLParser.HTMLParser):

    def __init__(self):
        self.reset()
        self.text_lines = []

    def handle_data(self, data):
        self.text_lines.append(data)

    def get_data(self):
        return ''.join(self.text_lines)


# Launchpad projects assigned for packages
_package_projects = {}

def find_launchpad_project(traceback, default="schooltool"):
    global _package_projects
    project = default
    while traceback is not None:
        frame = traceback.tb_frame
        package = frame.f_globals.get('__package__')
        while package:
            if package in _package_projects:
                project = _package_projects[package]
                break
            package = package.rpartition('.')[0]
        traceback = traceback.tb_next
    return project


def register_lauchpad_project(package, project):
    global _package_projects
    _package_projects[package] = project
