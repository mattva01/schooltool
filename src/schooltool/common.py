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
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
Things common to the SchoolTool server and clients.
"""

import re
import datetime

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
    m = re.match("(\d+)-(\d+)-(\d+)[ T](\d+):(\d+):(\d+)([.](\d+))?$", s)
    if not m:
        raise ValueError("Bad datetime: %s" % s)
    ssssss = m.groups()[7]
    if ssssss:
        ssssss = int((ssssss + "00000")[:6])
    else:
        ssssss = 0
    y, m, d, hh, mm, ss = map(int, m.groups()[:6])
    return datetime.datetime(y, m, d, hh, mm, ss, ssssss)


def dedent(text):
    r"""Remove leading indentation from tripple quoted strings.

    Example:

        >>> dedent('''
        ...     some text
        ...     is here
        ...        with maybe some indents
        ...     ''')
        ...
        'some text\nis here\n   with maybe some indents\n'

    Corner cases (mixing tabs and spaces, lines that are indented less than
    the first line) are not handled yet.
    """
    lines = text.splitlines()
    first, limit = 0, len(lines)
    while first < limit and not lines[first]:
        first += 1
    if first >= limit:
        return ''
    firstline = lines[first]
    indent, limit = 0, len(firstline)
    while indent < limit and firstline[indent] in (' ', '\t'):
        indent += 1
    return '\n'.join([line[indent:] for line in lines[first:]])
