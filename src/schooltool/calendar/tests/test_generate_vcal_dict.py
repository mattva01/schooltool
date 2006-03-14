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
Unit tests for schooltool.calendar.generate_vcal_dict

$Id$
"""
import unittest

from zope.testing import doctest


def doctest_extract_tzlocation():
    """Tests for extract_tzlocation.

    Extracts tzlocation from a combination of a path and a filename:

        >>> from schooltool.calendar.generate_vcal_dict import extract_tzlocation
        >>> extract_tzlocation("/foo/bar/baz", "/foo/bar/baz/America/Foo.ics")
        'America/Foo'

    even if the id has more than 2 parts:

        >>> extract_tzlocation("/foo/bar/baz",
        ...                    "/foo/bar/baz/America/Indiana/Foo.ics")
        'America/Indiana/Foo'

    non-absolute paths are supported too:

        >>> extract_tzlocation(".", "./America/Foo.ics")
        'America/Foo'
        >>> extract_tzlocation(".", "./America/Indiana/Foo.ics")
        'America/Indiana/Foo'

    """


def doctest_walk_ics():
    """Tests for walk_ics.

        >>> from schooltool.calendar.generate_vcal_dict import walk_ics
        >>> import schooltool.calendar.tests as tests
        >>> import os
        >>> path = os.path.dirname(tests.__file__)
        >>> tzinfo = list(walk_ics(path))
        Timezone 'sample' was not found

    There are 2 timezone files in the test directory:

        >>> len(tzinfo)
        2

        >>> location, tzid, vtimezone = tzinfo[0]

    One of them is for Amsterdam:

        >>> location
        'Europe/Amsterdam'

        >>> tzid
        '/schooltool.org/Olson_20060310_1/Europe/Amsterdam'

    The proper VTIMEZONE block is extracted from the file:

        >>> print vtimezone
        BEGIN:VTIMEZONE
        TZID:/schooltool.org/Olson_20060310_1/Europe/Amsterdam
        X-LIC-LOCATION:Europe/Amsterdam
        BEGIN:DAYLIGHT
        TZOFFSETFROM:+0100
        TZOFFSETTO:+0200
        TZNAME:CEST
        DTSTART:19700329T020000
        RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU
        END:DAYLIGHT
        BEGIN:STANDARD
        TZOFFSETFROM:+0200
        TZOFFSETTO:+0100
        TZNAME:CET
        DTSTART:19701025T030000
        RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU
        END:STANDARD
        END:VTIMEZONE

    The other one is for Vilnius:

        >>> location, tzid, vtimezone = tzinfo[1]
        >>> location
        'Europe/Vilnius'

    """


def test_suite():
    return doctest.DocTestSuite()

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
