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
from zope.app.annotation.interfaces import IAttributeAnnotatable
from zope.app.testing import setup, ztapi
from schooltool.timetable.tests.test_timetable import Content, Parent
from schooltool.timetable.interfaces import ITimetables
from schooltool.timetable import TimetablesAdapter
from zope.interface.verify import verifyObject


class BaseTimetableSourceTest(object):

    def setUp(self):
        from schooltool.relationship.tests import setUpRelationships

        self.site = setup.placefulSetUp(True)
        setup.setUpAnnotations()
        setUpRelationships()

        ztapi.provideAdapter(IAttributeAnnotatable, ITimetables,
                             TimetablesAdapter)

    def tearDown(self):
        setup.placefulTearDown()

    def test(self):
        from schooltool.timetable.interfaces import ITimetableSource
        context = ITimetables(Content())
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

        tm = ITimetables(Content())
        parent = Parent()
        self.createRelationship(tm.object, parent)

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

        adapter = self.createAdapter(tm)
        result = adapter.getTimetable("2003 fall", "sequential")
        self.assertEqual(result, composite)

        # nonexising
        result = adapter.getTimetable("2005 fall", "sequential")
        self.assertEqual(result, None)

        # let's try it with two timetables
        otherparent = Parent()
        self.createRelationship(tm.object, otherparent)

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
        from schooltool.timetable import TimetableActivity

        tm = ITimetables(Content())

        adapter = self.createAdapter(tm)
        self.assertEqual(adapter.listTimetables(), Set())

        parent = Parent()
        self.createRelationship(tm.object, parent)

        parent.listCompositeTimetables = (
            lambda: Set([("2003 fall", "sequential")]))

        self.assertEqual(adapter.listTimetables(),
                         Set([("2003 fall", "sequential")]))

        otherparent = Parent()
        self.createRelationship(tm.object, otherparent)

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


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestMembershipTimetableSource))
    suite.addTest(unittest.makeSuite(TestInstructionTimetableSource))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
