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


def parse_datetime(s):
    """Parse a ISO 8601 date/time value.

    Only a small subset of ISO 8601 is accepted:

      YYYY-MM-DD HH:MM:SS
      YYYY-MM-DD HH:MM:SS.ssssss
      YYYY-MM-DDTHH:MM:SS
      YYYY-MM-DDTHH:MM:SS.ssssss

    Returns a datetime.datetime object without a time zone.
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
