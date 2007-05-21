#
#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2007 Shuttleworth Foundation
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
Unit tests for lyceum journal.

$Id$
"""
import unittest

from zope.component import provideAdapter
from zope.app.testing import setup
from zope.testing import doctest


def doctest_LyceumJournal():
    """Tests for LyceumJournal

        >>> from lyceum.journal.journal import LyceumJournal
        >>> journal = LyceumJournal()

    Journals don't really work on their own, as they find out which
    section they belong to by their __name__:

        >>> journal.__name__ = 'some_section'

        >>> class SectionStub(object):
        ...     pass
        >>> section = SectionStub()

        >>> class STAppStub(dict):
        ...     def __init__(self, context):
        ...         self['sections'] = {'some_section': section}

        >>> from schooltool.app.interfaces import ISchoolToolApplication
        >>> provideAdapter(STAppStub, adapts=[None], provides=ISchoolToolApplication)

        >>> journal.section is section
        True

    Grades can be added for every person/meeting pair:

        >>> class PersonStub(object):
        ...     def __init__(self, name):
        ...         self.__name__ = name

        >>> class MeetingStub(object):
        ...     def __init__(self, uid):
        ...         self.unique_id = uid

        >>> person1 = PersonStub('john')
        >>> person2 = PersonStub('pete')

        >>> meeting = MeetingStub('some-unique-id')

        >>> journal.setGrade(person1, meeting, "5")

    And are read that way too:

        >>> journal.getGrade(person1, meeting)
        '5'

    If there is no grade present in that position, you get None:

        >>> journal.getGrade(person2, meeting) is None
        True

    Unless default is provided:

        >>> journal.getGrade(person2, meeting, default="")
        ''

    """


def doctest_LyceumJournal():
    """Tests for getSectionLyceumJournal

        >>> from lyceum.journal.journal import getSectionLyceumJournal

        >>> from zope.app.container.btree import BTreeContainer
        >>> journal_container = BTreeContainer()
        >>> class STAppStub(dict):
        ...     def __init__(self, context):
        ...         self['lyceum.journal'] = journal_container

        >>> from schooltool.app.interfaces import ISchoolToolApplication
        >>> provideAdapter(STAppStub, adapts=[None], provides=ISchoolToolApplication)

        >>> class SectionStub(object):
        ...     def __init__(self, name):
        ...         self.__name__ = name

        >>> section = SectionStub('some_section')

    Initially the journal container is empty, but if we try to get a
    journal for a section, a LyceumJournal objecgt is created:

        >>> journal = getSectionLyceumJournal(section)
        >>> journal
        <lyceum.journal.journal.LyceumJournal object at ...>

        >>> journal.__name__
        u'some_section'

        >>> journal_container[section.__name__] is journal
        True

    If we try to get the journal for the second time, we get the same
    journal instance:

        >>> getSectionLyceumJournal(section) is journal
        True

    """


def setUp(test):
    setup.placelessSetUp()


def tearDown(test):
    setup.placelessTearDown()


def test_suite():
    optionflags = doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS
    return doctest.DocTestSuite(optionflags=optionflags,
                                setUp=setUp, tearDown=tearDown)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
