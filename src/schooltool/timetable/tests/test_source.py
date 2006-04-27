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
Unit tests for the schooltool.timetable.source module.

$Id$
"""
import unittest
from sets import Set

from zope.annotation.interfaces import IAttributeAnnotatable
from zope.app.testing import setup, ztapi
from zope.testing import doctest
from schooltool.timetable.tests.test_timetable import ContentStub, Parent
from schooltool.timetable.interfaces import ITimetables
from schooltool.timetable.interfaces import IOwnTimetables
from schooltool.timetable.interfaces import IHaveTimetables
from schooltool.timetable.interfaces import ICompositeTimetables
from schooltool.timetable import CompositeTimetables
from schooltool.timetable import TimetablesAdapter
from zope.interface.verify import verifyObject


class BaseTimetableSourceTest(object):

    def setUp(self):
        from schooltool.relationship.tests import setUpRelationships

        self.site = setup.placefulSetUp(True)
        setup.setUpAnnotations()
        setUpRelationships()
        ztapi.provideAdapter(IOwnTimetables, ITimetables,
                             TimetablesAdapter)
        class CompositeTimetablesStub(object):
            def __init__(self, context):
                self.context = context
            def listCompositeTimetables(self):
                return self.context.listCompositeTimetables()
            def getCompositeTimetable(self, *args):
                return self.context.getCompositeTimetable(*args)
        ztapi.provideAdapter(IHaveTimetables, ICompositeTimetables,
                             CompositeTimetablesStub)

    def tearDown(self):
        setup.placefulTearDown()

    def test(self):
        from schooltool.timetable.interfaces import ITimetableSource
        context = ContentStub()
        adapter = self.createAdapter(context)
        verifyObject(ITimetableSource, adapter)

    def newTimetable(self):
        from schooltool.timetable import Timetable, TimetableDay
        tt = Timetable(("A", "B"))
        tt["A"] = TimetableDay(["Green", "Blue"])
        tt["B"] = TimetableDay(["Green", "Blue"])
        return tt

    def test_getTimetable(self):
        from schooltool.timetable import TimetableActivity

        content = ContentStub()
        parent = Parent()
        self.createRelationship(content, parent)

        composite = self.newTimetable()
        english = TimetableActivity("English")
        composite["A"].add("Green", english)

        def newComposite(term_id, schema_id):
            if (term_id, schema_id) == ("2003 fall", "sequential"):
                return composite
            else:
                return None

        parent.getCompositeTimetable = newComposite
        parent.listCompositeTimetables = (
            lambda: Set([("2003 fall", "sequential")]))

        adapter = self.createAdapter(content)
        result = adapter.getTimetable("2003 fall", "sequential")
        self.assertEqual(result, composite)

        # nonexising
        result = adapter.getTimetable("2005 fall", "sequential")
        self.assertEqual(result, None)

        # let's try it with two timetables
        otherparent = Parent()
        self.createRelationship(content, otherparent)

        othertt = self.newTimetable()
        math = TimetableActivity("Math")
        othertt["A"].add("Blue", math)

        otherparent.getCompositeTimetable = lambda x, y: othertt

        expected = composite.cloneEmpty()
        expected.update(composite)
        expected.update(othertt)

        result = adapter.getTimetable("2003 fall", "sequential")
        self.assertEqual(result, expected)

    def test_listTimetables(self):
        content = ContentStub()

        adapter = self.createAdapter(content)
        self.assertEqual(adapter.listTimetables(), Set())

        parent = Parent()
        self.createRelationship(content, parent)

        parent.listCompositeTimetables = (
            lambda: Set([("2003 fall", "sequential")]))

        self.assertEqual(adapter.listTimetables(),
                         Set([("2003 fall", "sequential")]))

        otherparent = Parent()
        self.createRelationship(content, otherparent)

        otherparent.listCompositeTimetables = (
            lambda: Set([("2005 fall", "sequential")]))

        self.assertEqual(adapter.listTimetables(),
                         Set([("2003 fall", "sequential"),
                              ("2005 fall", "sequential")]))


class TestMembershipTimetableSource(BaseTimetableSourceTest,
                                    unittest.TestCase):

    def createAdapter(self, context):
        from schooltool.timetable.source import MembershipTimetableSource
        return MembershipTimetableSource(context)

    def createRelationship(self, context, related):
        from schooltool.app.membership import Membership
        Membership(group=related, member=context)


class TestInstructionTimetableSource(BaseTimetableSourceTest,
                                     unittest.TestCase):

    def createAdapter(self, context):
        from schooltool.timetable.source import InstructionTimetableSource
        return InstructionTimetableSource(context)

    def createRelationship(self, context, related):
        from schooltool.app.relationships import Instruction
        Instruction(instructor=context, section=related)


def doctest_OwnedTimetableSource():
    """Tests for OwnedTimetableSource

        >>> from schooltool.timetable.source import OwnedTimetableSource
        >>> from zope.interface import implements
        >>> class Timetables(object):
        ...     timetables = {}

        >>> class TTOwnerStub(object):
        ...     implements(IOwnTimetables)
        ...     timetables = Timetables()
        ...     def __conform__(self, iface):
        ...         if iface == ITimetables:
        ...             return self.timetables

        >>> owner = TTOwnerStub()
        >>> source = OwnedTimetableSource(owner)

        >>> source.getTimetable("2003", "autumn") is None
        True

        >>> source.listTimetables()
        Set([])

        >>> ITimetables(owner).timetables = {'2003.autumn': "a timetable",
        ...                                  '2005.spring': "a pine corn"}
        >>> source.listTimetables()
        Set([('2003', 'autumn'), ('2005', 'spring')])

        >>> source.getTimetable("2003", "autumn")
        'a timetable'

    """


def test_suite():
    return unittest.TestSuite([
        doctest.DocTestSuite(setUp=setup.placelessSetUp,
                             tearDown=setup.placelessTearDown),
        unittest.makeSuite(TestMembershipTimetableSource),
        unittest.makeSuite(TestInstructionTimetableSource)])
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
