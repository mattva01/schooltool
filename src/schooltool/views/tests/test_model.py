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
Unit tests for schooltool.views.model

$Id$
"""

import datetime
import unittest
import libxml2
from schooltool.tests.utils import RegistriesSetupMixin, EventServiceTestMixin
from schooltool.tests.utils import XMLCompareMixin
from schooltool.tests.helpers import diff, dedent
from schooltool.views.tests import RequestStub
from schooltool.views.tests import TraversableStub, TraversableRoot, setPath

__metaclass__ = type


class AbsenceTrackerStub:

    def __init__(self):
        self.absences = []


class TestApplicationObjectTraverserView(RegistriesSetupMixin,
                                         unittest.TestCase):

    def setUp(self):
        from schooltool.views.model import ApplicationObjectTraverserView
        from schooltool.model import Person
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.membership import Membership
        from schooltool import membership
        self.setUpRegistries()
        membership.setUp()
        app = Application()
        app['persons'] = ApplicationObjectContainer(Person)
        self.per = app['persons'].new("p", title="Pete")
        self.view = ApplicationObjectTraverserView(self.per)

    def test_traverse(self):
        from schooltool.views.facet import FacetManagementView
        from schooltool.views.relationship import RelationshipsView
        from schooltool.interfaces import IFacetManager

        request = RequestStub("http://localhost/people/p")
        result = self.view._traverse('relationships', request)
        self.assert_(isinstance(result, RelationshipsView))
        self.assert_(result.context is self.per)

        result = self.view._traverse('facets', request)
        self.assert_(isinstance(result, FacetManagementView))
        self.assert_(IFacetManager.isImplementedBy(result.context))

        self.assertRaises(KeyError, self.view._traverse, 'anything', request)


class TestPersonView(XMLCompareMixin, RegistriesSetupMixin, unittest.TestCase):

    def setUp(self):
        from schooltool.views.model import PersonView
        from schooltool.model import Group, Person
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.membership import Membership
        from schooltool import membership
        self.setUpRegistries()
        membership.setUp()
        app = Application()
        app['groups'] = ApplicationObjectContainer(Group)
        app['persons'] = ApplicationObjectContainer(Person)
        self.group = app['groups'].new("root", title="group")
        self.sub = app['groups'].new("subgroup", title="subgroup")
        self.per = app['persons'].new("p", title="Pete")

        Membership(group=self.group, member=self.sub)
        Membership(group=self.group, member=self.per)
        Membership(group=self.sub, member=self.per)

        self.view = PersonView(self.per)

    def test_traverse(self):
        from schooltool.views.facet import FacetManagementView
        from schooltool.views.relationship import RelationshipsView
        from schooltool.views.model import AbsenceManagementView
        from schooltool.views.timetable import TimetableTraverseView
        from schooltool.views.timetable import CompositeTimetableTraverseView
        from schooltool.interfaces import IFacetManager
        request = RequestStub("http://localhost/person")

        result = self.view._traverse('relationships', request)
        self.assert_(isinstance(result, RelationshipsView))
        self.assert_(result.context is self.per)

        result = self.view._traverse('facets', request)
        self.assert_(isinstance(result, FacetManagementView))
        self.assert_(IFacetManager.isImplementedBy(result.context))

        result = self.view._traverse('absences', request)
        self.assert_(isinstance(result, AbsenceManagementView))
        self.assert_(result.context is self.per)

        result = self.view._traverse('timetable', request)
        self.assert_(isinstance(result, TimetableTraverseView))
        self.assert_(result.context is self.per)

        result = self.view._traverse('composite-timetable', request)
        self.assert_(isinstance(result, CompositeTimetableTraverseView))
        self.assert_(result.context is self.per)

    def test_render(self):
        request = RequestStub("http://localhost/person")
        result = self.view.render(request)
        self.assertEquals(request.headers['Content-Type'],
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result, """
            <person xmlns:xlink="http://www.w3.org/1999/xlink">
              <name>Pete</name>
              <groups>
                <item xlink:type="simple" xlink:href="/groups/root"
                      xlink:title="group"/>
                <item xlink:type="simple" xlink:href="/groups/subgroup"
                      xlink:title="subgroup"/>
              </groups>
              <relationships xlink:type="simple"
                             xlink:title="Relationships"
                             xlink:href="p/relationships"/>
              <facets xlink:type="simple" xlink:title="Facets"
                      xlink:href="p/facets"/>
            </person>
            """, recursively_sort=['groups'])


class TestGroupView(XMLCompareMixin, RegistriesSetupMixin, unittest.TestCase):

    def setUp(self):
        from schooltool.views.model import GroupView
        from schooltool.model import Group, Person
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.membership import Membership
        from schooltool import membership
        self.setUpRegistries()
        membership.setUp()
        app = Application()
        app['groups'] = ApplicationObjectContainer(Group)
        app['persons'] = ApplicationObjectContainer(Person)
        self.group = app['groups'].new("root", title="group")
        self.sub = app['groups'].new("subgroup", title="subgroup")
        self.per = app['persons'].new("p", title="p")

        Membership(group=self.group, member=self.sub)
        Membership(group=self.group, member=self.per)

        self.view = GroupView(self.group)

    def tearDown(self):
        self.tearDownRegistries()

    def test_render(self):
        from schooltool.component import getPath
        request = RequestStub("http://localhost/group/")
        result = self.view.render(request)
        self.assertEquals(request.headers['Content-Type'],
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result, """
            <group xmlns:xlink="http://www.w3.org/1999/xlink">
              <name>group</name>
              <item xlink:type="simple" xlink:title="p"
                    xlink:href="%s"/>
              <item xlink:type="simple" xlink:title="subgroup"
                    xlink:href="%s"/>
              <facets xlink:type="simple" xlink:title="Facets"
                      xlink:href="root/facets"/>
              <relationships xlink:type="simple" xlink:title="Relationships"
                             xlink:href="root/relationships"/>
            </group>
            """ % (getPath(self.per), getPath(self.sub)),
            recursively_sort=['group'])

    def test_traverse(self):
        from schooltool.views.facet import FacetManagementView
        from schooltool.views.relationship import RelationshipsView
        from schooltool.views.model import RollcallView, TreeView
        from schooltool.interfaces import IFacetManager
        request = RequestStub("http://localhost/group")

        result = self.view._traverse('relationships', request)
        self.assert_(isinstance(result, RelationshipsView))
        self.assert_(result.context is self.group)

        result = self.view._traverse('facets', request)
        self.assert_(isinstance(result, FacetManagementView))
        self.assert_(IFacetManager.isImplementedBy(result.context))

        result = self.view._traverse("rollcall", request)
        self.assert_(isinstance(result, RollcallView))
        self.assert_(result.context is self.group)

        result = self.view._traverse("tree", request)
        self.assert_(isinstance(result, TreeView))
        self.assert_(result.context is self.group)

        self.assertRaises(KeyError, self.view._traverse, "otherthings",
                          request)


class TestTreeView(XMLCompareMixin, RegistriesSetupMixin, unittest.TestCase):

    def setUp(self):
        from schooltool.model import Group, Person
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.membership import Membership
        from schooltool import membership
        self.setUpRegistries()
        membership.setUp()
        app = Application()
        app['groups'] = ApplicationObjectContainer(Group)
        app['persons'] = ApplicationObjectContainer(Person)
        self.group = app['groups'].new("root", title="root group")
        self.group1 = app['groups'].new("group1", title="group1")
        self.group2 = app['groups'].new("group2", title="group2")
        self.group1a = app['groups'].new("group1a", title="group1a")
        self.group1b = app['groups'].new("group1b", title="group1b")
        self.persona = app['persons'].new("a", title="a")

        Membership(group=self.group, member=self.group1)
        Membership(group=self.group, member=self.group2)
        Membership(group=self.group1, member=self.group1a)
        Membership(group=self.group1, member=self.group1b)
        Membership(group=self.group2, member=self.persona)

        libxml2.registerErrorHandler(lambda ctx, error: None, None)

    def test(self):
        from schooltool.views.model import TreeView
        view = TreeView(self.group)
        request = RequestStub("http://localhost/groups/root/tree")
        result = view.render(request)
        self.assertEquals(request.headers['Content-Type'],
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result, """
            <tree xmlns:xlink="http://www.w3.org/1999/xlink">
              <group xlink:type="simple" xlink:href="/groups/root"
                     xlink:title="root group">
                <group xlink:type="simple" xlink:href="/groups/group2"
                       xlink:title="group2">
                </group>
                <group xlink:type="simple" xlink:href="/groups/group1"
                       xlink:title="group1">
                  <group xlink:type="simple" xlink:href="/groups/group1a"
                         xlink:title="group1a">
                  </group>
                  <group xlink:type="simple" xlink:href="/groups/group1b"
                         xlink:title="group1b">
                  </group>
                </group>
              </group>
            </tree>
            """, recursively_sort=['tree'])


class TestAbsenceCommentParser(unittest.TestCase):

    def test_parseComment(self):
        from schooltool.interfaces import Unchanged
        from schooltool.views.model import AbsenceCommentParser
        john = object()
        group = object()
        persons = TraversableStub(john=john)
        groups = TraversableStub(aa=group)
        root = TraversableRoot(persons=persons, groups=groups)
        parser = AbsenceCommentParser()
        parser.context = root

        # The very minimum
        request = RequestStub(body="""
                        text="Foo"
                        reporter="/persons/john"
                    """)
        lower_limit = datetime.datetime.utcnow()
        comment = parser.parseComment(request)
        upper_limit = datetime.datetime.utcnow()
        self.assertEquals(comment.text, "Foo")
        self.assertEquals(comment.reporter, john)
        self.assert_(lower_limit <= comment.datetime <= upper_limit)
        self.assert_(comment.absent_from is None)
        self.assert_(comment.ended is Unchanged)
        self.assert_(comment.resolved is Unchanged)
        self.assert_(comment.expected_presence is Unchanged)

        # Everything
        request = RequestStub(body="""
                        text="Foo"
                        reporter="/persons/john"
                        absent_from="/groups/aa"
                        ended="ended"
                        resolved="unresolved"
                        datetime="2004-04-04 04:04:04"
                        expected_presence="2005-05-05 05:05:05"
                    """)
        comment = parser.parseComment(request)
        self.assertEquals(comment.text, "Foo")
        self.assertEquals(comment.reporter, john)
        self.assertEquals(comment.absent_from, group)
        self.assertEquals(comment.ended, True)
        self.assertEquals(comment.resolved, False)
        self.assertEquals(comment.datetime,
                          datetime.datetime(2004, 4, 4, 4, 4, 4))
        self.assertEquals(comment.expected_presence,
                          datetime.datetime(2005, 5, 5, 5, 5, 5))

        # Clearing Expected presence
        request = RequestStub(body="""
                        text="Foo"
                        reporter="/persons/john"
                        expected_presence=""
                    """)
        comment = parser.parseComment(request)
        self.assert_(comment.expected_presence is None)

    def test_parseComment_errors(self):
        from schooltool.views.model import AbsenceCommentParser
        parser = AbsenceCommentParser()
        parser.context = TraversableRoot(obj=object())
        bad_requests = (
            '',
            'reporter="/obj"',
            'text=""',
            'text="" reporter="/does/not/exist"',
            'text="" reporter="/obj" datetime="now"',
            'text="" reporter="/obj" absent_from="/does/not/exist"',
            'text="" reporter="/obj" ended="mu"',
            'text="" reporter="/obj" resolved="mu"',
            'text="" reporter="/obj" expected_presence="dunno"',
        )
        for body in bad_requests:
            request = RequestStub(body=body)
            try:
                parser.parseComment(request)
            except ValueError:
                pass
            else:
                self.fail("did not raise ValueError for\n\t%s" % body)


class TestAbsenceManagementView(XMLCompareMixin, EventServiceTestMixin,
                                unittest.TestCase):

    def test_traverse(self):
        from schooltool.views.model import AbsenceManagementView, AbsenceView
        from schooltool.model import Person, AbsenceComment
        context = Person()
        setPath(context, '/person', root=self.serviceManager)
        absence = context.reportAbsence(AbsenceComment())
        view = AbsenceManagementView(context)
        request = RequestStub("http://localhost/person/absences")
        result = view._traverse(absence.__name__, request)
        self.assert_(isinstance(result, AbsenceView))
        self.assert_(result.context is absence)
        self.assertRaises(KeyError,
                          view._traverse, absence.__name__ + 'X', request)

    def test_get(self):
        from schooltool.views.model import AbsenceManagementView
        from schooltool.model import Person, AbsenceComment
        context = Person()
        setPath(context, '/person', root=self.serviceManager)
        dt = datetime.datetime(2001, 2, 3, 4, 5, 6)
        context.reportAbsence(AbsenceComment(dt=dt, ended=True, resolved=True))
        context.reportAbsence(AbsenceComment(dt=dt))
        self.assertEquals(len(list(context.iterAbsences())), 2)
        view = AbsenceManagementView(context)
        request = RequestStub("http://localhost/person/absences")
        result = view.render(request)
        self.assertEquals(request.headers['Content-Type'],
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result, """
            <absences xmlns:xlink="http://www.w3.org/1999/xlink">
              <absence xlink:type="simple" xlink:href="/person/absences/001"
                       xlink:title="001" datetime="2001-02-03 04:05:06"
                       ended="ended" resolved="resolved"/>
              <absence xlink:type="simple" xlink:href="/person/absences/002"
                       xlink:title="002" datetime="2001-02-03 04:05:06"
                       ended="unended" resolved="unresolved"/>
            </absences>
            """, recursively_sort=['absences'])

    def test_post(self):
        from schooltool.views.model import AbsenceManagementView
        from schooltool.model import Person
        context = Person()
        setPath(context, '/person', root=self.serviceManager)
        basepath = "/person/absences/"
        baseurl = "http://localhost%s" % basepath
        view = AbsenceManagementView(context)
        request = RequestStub(baseurl[:-1], method="POST",
                    body='text="Foo" reporter="."')

        result = view.render(request)

        self.assertEquals(request.code, 201)
        self.assertEquals(request.reason, "Created")
        location = request.headers['Location']
        self.assert_(location.startswith(baseurl),
                     "%r.startswith(%r) failed" % (location, baseurl))
        name = location[len(baseurl):]
        self.assertEquals(request.headers['Content-Type'], "text/plain")
        path = '%s%s' % (basepath, name)
        self.assert_(path in result, '%r not in %r' % (path, result))
        self.assertEquals(len(list(context.iterAbsences())), 1)
        absence = context.getAbsence(name)
        comment = absence.comments[0]
        self.assertEquals(comment.text, "Foo")

    def test_post_another_one(self):
        from schooltool.views.model import AbsenceManagementView
        from schooltool.model import Person, AbsenceComment
        context = Person()
        setPath(context, '/person', root=self.serviceManager)
        absence = context.reportAbsence(AbsenceComment())
        basepath = "/person/absences/"
        baseurl = "http://localhost%s" % basepath
        view = AbsenceManagementView(context)
        request = RequestStub(baseurl[:-1], method="POST",
                    body='text="Bar" reporter="."')

        result = view.render(request)

        self.assertEquals(request.code, 200)
        self.assertEquals(request.reason, "OK")
        location = request.headers['Location']
        self.assert_(location.startswith(baseurl),
                     "%r.startswith(%r) failed" % (location, baseurl))
        name = location[len(baseurl):]
        self.assertEquals(request.headers['Content-Type'], "text/plain")
        path = '%s%s' % (basepath, name)
        self.assert_(path in result, '%r not in %r' % (path, result))
        self.assertEquals(len(list(context.iterAbsences())), 1)
        self.assertEquals(name, absence.__name__)
        comment = absence.comments[-1]
        self.assertEquals(comment.text, "Bar")

    def test_post_errors(self):
        from schooltool.views.model import AbsenceManagementView
        from schooltool.model import Person
        context = Person()
        setPath(context, '/person', root=self.serviceManager)
        basepath = "/person/absences/"
        baseurl = "http://localhost%s" % basepath
        view = AbsenceManagementView(context)
        request = RequestStub(baseurl[:-1], method="POST",
                    body='')

        result = view.render(request)

        self.assertEquals(request.code, 400)
        self.assertEquals(request.reason, "Bad Request")
        self.assertEquals(request.headers['Content-Type'], "text/plain")
        self.assertEquals(result, "Text attribute missing")


class TestAbsenceView(XMLCompareMixin, EventServiceTestMixin,
                      unittest.TestCase):

    def createAbsence(self):
        from schooltool.model import Person, Group, AbsenceComment
        reporter1 = Person(title="Reporter 1")
        setPath(reporter1, '/reporter1')
        reporter2 = Person(title="Reporter 2")
        setPath(reporter2, '/reporter2')
        group1 = Group(title="Group 1")
        setPath(group1, '/group1')
        person = Person(title="A Person")
        setPath(person, '/person', root=self.serviceManager)
        absence = person.reportAbsence(AbsenceComment(reporter1, 'Some text',
                dt=datetime.datetime(2001, 1, 1)))
        person.reportAbsence(AbsenceComment(reporter2, 'More text\n',
                absent_from=group1, dt=datetime.datetime(2002, 2, 2),
                expected_presence=datetime.datetime(2003, 03, 03),
                ended=True, resolved=False))
        return absence

    def test_get(self):
        from schooltool.views.model import AbsenceView
        absence = self.createAbsence()
        view = AbsenceView(absence)
        request = RequestStub("http://localhost/person/absences/001")
        result = view.render(request)
        self.assertEquals(request.headers['Content-Type'],
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result, """
            <absence xmlns:xlink="http://www.w3.org/1999/xlink"
                     resolved="unresolved" ended="ended"
                     expected_presence="2003-03-03 00:00:00">
              <person xlink:type="simple" xlink:title="A Person"
                      xlink:href="/person"/>
              <comment datetime="2001-01-01 00:00:00">
                <reporter xlink:type="simple" xlink:title="Reporter 1"
                          xlink:href="/reporter1"/>
                <text>Some text</text>
              </comment>
              <comment datetime="2002-02-02 00:00:00" ended="ended"
                       resolved="unresolved"
                       expected_presence="2003-03-03 00:00:00">
                <reporter xlink:type="simple" xlink:title="Reporter 2"
                          xlink:href="/reporter2"/>
                <absentfrom xlink:type="simple" xlink:title="Group 1"
                            xlink:href="/group1"/>
                <text>More text</text>
              </comment>
            </absence>
            """, recursively_sort=['absence'])

    def test_post(self):
        from schooltool.views.model import AbsenceView
        absence = self.createAbsence()
        view = AbsenceView(absence)
        basepath = "/person/absences/001/"
        baseurl = "http://localhost" + basepath
        request = RequestStub(baseurl[:-1], method="POST",
                    body='text="Foo" reporter="."')
        result = view.render(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(request.reason, "OK")
        self.assertEquals(request.headers['Content-Type'], "text/plain")
        self.assertEquals(result, "Comment added")
        comment = absence.comments[-1]
        self.assertEquals(comment.text, "Foo")

    def test_post_errors(self):
        from schooltool.views.model import AbsenceView
        absence = self.createAbsence()
        self.assertEquals(len(absence.comments), 2)
        basepath = "/person/absences/001/"
        setPath(absence, basepath[:-1])
        baseurl = "http://localhost" + basepath
        request = RequestStub(baseurl[:-1], method="POST",
                    body='text="Foo" reporter="/does/not/exist"')
        view = AbsenceView(absence)
        result = view.render(request)
        self.assertEquals(request.code, 400)
        self.assertEquals(request.reason, "Bad Request")
        self.assertEquals(request.headers['Content-Type'], "text/plain")
        self.assertEquals(result, "Reporter not found: /does/not/exist")
        self.assertEquals(len(absence.comments), 2)

    def test_post_duplicate(self):
        from schooltool.views.model import AbsenceView
        from schooltool.model import AbsenceComment
        absence = self.createAbsence()
        absence.person.reportAbsence(AbsenceComment())
        self.assertEquals(len(absence.comments), 2)
        basepath = "/person/absences/001/"
        setPath(absence, basepath[:-1])
        baseurl = "http://localhost" + basepath
        request = RequestStub(baseurl[:-1], method="POST",
                    body='text="Foo" reporter="." ended="unended"')
        view = AbsenceView(absence)
        result = view.render(request)
        self.assertEquals(request.code, 400)
        self.assertEquals(request.reason, "Bad Request")
        self.assertEquals(request.headers['Content-Type'], "text/plain")
        self.assertEquals(result,
            "Cannot reopen an absence when another one is not ended")
        self.assertEquals(len(absence.comments), 2)


class TestRollcallView(XMLCompareMixin, RegistriesSetupMixin,
                       unittest.TestCase):

    def setUp(self):
        from schooltool.model import Group, Person
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.membership import Membership
        from schooltool import membership
        self.setUpRegistries()
        membership.setUp()
        app = Application()
        app['groups'] = ApplicationObjectContainer(Group)
        app['persons'] = ApplicationObjectContainer(Person)
        self.group = app['groups'].new("root", title="group")
        self.sub = app['groups'].new("subgroup", title="subgroup")
        self.subsub = app['groups'].new("subsubgroup", title="subsubgroup")
        self.sub2 = app['groups'].new("subgroup2", title="subgroup")
        self.persona = app['persons'].new("a", title="a")
        self.personb = app['persons'].new("b", title="b")
        self.personc = app['persons'].new("c", title="c")
        self.persond = app['persons'].new("d", title="d")
        self.personq = app['persons'].new("q", title="q")

        Membership(group=self.group, member=self.sub)
        Membership(group=self.sub, member=self.subsub)
        Membership(group=self.group, member=self.persona)
        Membership(group=self.sub, member=self.personb)
        Membership(group=self.subsub, member=self.personc)
        Membership(group=self.subsub, member=self.persond)
        # a person can belong to more than one group
        Membership(group=self.subsub, member=self.persona)
        Membership(group=self.sub2, member=self.personb)

        libxml2.registerErrorHandler(lambda ctx, error: None, None)

    def test_get(self):
        from schooltool.views.model import RollcallView
        from schooltool.model import AbsenceComment
        self.personb.reportAbsence(AbsenceComment())
        self.personc.reportAbsence(AbsenceComment(None, "",
                expected_presence=datetime.datetime(2001, 1, 1, 2, 2, 2)))
        view = RollcallView(self.group)
        request = RequestStub("http://localhost/group/rollcall")
        result = view.render(request)
        self.assertEquals(request.headers['Content-Type'],
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result, """
            <rollcall xmlns:xlink="http://www.w3.org/1999/xlink"
                      xlink:type="simple" xlink:title="group"
                      xlink:href="/groups/root">
              <person xlink:type="simple" xlink:href="/persons/a"
                      xlink:title="a" presence="present"/>
              <person xlink:type="simple" xlink:href="/persons/b"
                      xlink:title="b" presence="absent"/>
              <person xlink:type="simple" xlink:href="/persons/c"
                      xlink:title="c"
                      expected_presence="2001-01-01 02:02:02"
                      presence="absent"/>
              <person xlink:type="simple" xlink:href="/persons/d"
                      xlink:title="d" presence="present"/>
            </rollcall>
            """, recursively_sort=['rollcall'])

    def test_post(self):
        from schooltool.views.model import RollcallView
        from schooltool.model import AbsenceComment
        personc_absence = self.personc.reportAbsence(AbsenceComment())
        persond_absence = self.persond.reportAbsence(AbsenceComment())
        view = RollcallView(self.group)
        text = "I just did a roll call and noticed Mr. B. is missing again"
        request = RequestStub("http://localhost/group/rollcall",
                              method="POST", body="""
            <rollcall xmlns:xlink="http://www.w3.org/1999/xlink"
                      xlink:type="simple" xlink:title="group"
                      xlink:href="/groups/root"
                      datetime="2001-02-03 04:05:06">
              <reporter xlink:type="simple" xlink:href="/persons/a" />
              <person xlink:type="simple" xlink:href="/persons/a"
                      xlink:title="a" presence="present"/>
              <person xlink:type="simple" xlink:href="/persons/b"
                      xlink:title="b" presence="absent"
                      comment="%s"/>
              <person xlink:type="simple" xlink:href="/persons/c"
                      xlink:title="c" presence="present" resolved="resolved"/>
              <person xlink:type="simple" xlink:href="/persons/d"
                      xlink:title="d" presence="absent"/>
            </rollcall>
                              """ % text)
        result = view.render(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(request.reason, "OK")
        self.assertEquals(request.headers['Content-Type'], "text/plain")
        self.assertEquals(result, "2 absences and 1 presences reported")

        # persona was present and is present, no comments should be added.
        self.assertEqual(len(list(self.persona.iterAbsences())), 0)

        # personb was present, now should be absent
        absence = self.personb.getCurrentAbsence()
        self.assert_(absence is not None)
        comment = absence.comments[-1]
        self.assert_(comment.absent_from is self.group)
        self.assert_(comment.reporter is self.persona)
        self.assertEquals(comment.text, text)
        self.assertEquals(comment.datetime,
                          datetime.datetime(2001, 2, 3, 4, 5, 6))

        # personc was absent, now should be present
        self.assert_(self.personc.getCurrentAbsence() is None)
        comment = personc_absence.comments[-1]
        self.assert_(comment.absent_from is self.group)
        self.assert_(comment.reporter is self.persona)
        self.assertEquals(comment.text, None)
        self.assertEquals(comment.ended, True)
        self.assertEquals(comment.resolved, True)
        self.assertEquals(comment.datetime,
                          datetime.datetime(2001, 2, 3, 4, 5, 6))

        # persond was absent, now should be absent
        absence = self.persond.getCurrentAbsence()
        self.assert_(absence is persond_absence)
        comment = absence.comments[-1]
        self.assert_(comment.absent_from is self.group)
        self.assert_(comment.reporter is self.persona)
        self.assertEquals(comment.text, None)
        self.assertEquals(comment.datetime,
                          datetime.datetime(2001, 2, 3, 4, 5, 6))

    def post_errors(self, body, errmsg):
        from schooltool.views.model import RollcallView
        view = RollcallView(self.group)
        request = RequestStub("http://localhost/group/rollcall",
                              method="POST", body=body)
        result = view.render(request)
        self.assertEquals(request.code, 400)
        self.assertEquals(request.reason, "Bad Request")
        self.assertEquals(request.headers['Content-Type'], "text/plain")
        self.assertEquals(result, errmsg)

    def test_post_syntax_errors(self):
        self.post_errors("""This is not a roll call""",
            "Bad roll call representation")

    def test_post_structure_errors(self):
        # I expect that we can validate all these errors with a schema
        # and just return a generic "Bad roll call representation" error
        self.post_errors("""
            <rollcall xmlns:xlink="http://www.w3.org/1999/xlink"
                      xlink:type="simple" xlink:title="group"
                      xlink:href="/groups/root"
                      datetime="2001-02-03 04:05:06">
              <comment>A comment</comment>
              <person xlink:type="simple" xlink:href="/persons/a"
                      xlink:title="a" presence="present"/>
              <person xlink:type="simple" xlink:href="/persons/b"
                      xlink:title="b" presence="absent"/>
              <person xlink:type="simple" xlink:href="/persons/c"
                      xlink:title="c" presence="present"/>
              <person xlink:type="simple" xlink:href="/persons/d"
                      xlink:title="d" presence="absent"/>
            </rollcall>""",
            "Reporter not specified")
        self.post_errors("""
            <rollcall xmlns:xlink="http://www.w3.org/1999/xlink"
                      xlink:type="simple" xlink:title="group"
                      xlink:href="/groups/root"
                      datetime="2001-02-03 04:05:06">
              <reporter xlink:type="simple" xlink:href="/persons/a" />
              <comment>A comment</comment>
              <person xlink:type="simple" xlink:href="/persons/a"
                      xlink:title="a" presence="present"/>
              <person xlink:type="simple"
                      xlink:title="b" presence="absent"/>
              <person xlink:type="simple" xlink:href="/persons/c"
                      xlink:title="c" presence="present"/>
              <person xlink:type="simple" xlink:href="/persons/d"
                      xlink:title="d" presence="absent"/>
            </rollcall>""",
            "Person does not specify xlink:href")
        self.post_errors("""
            <rollcall xmlns:xlink="http://www.w3.org/1999/xlink"
                      xlink:type="simple" xlink:title="group"
                      xlink:href="/groups/root"
                      datetime="2001-02-03 04:05:06">
              <reporter xlink:type="simple" xlink:href="/persons/a" />
              <comment>A comment</comment>
              <person xlink:type="simple" xlink:href="/persons/a"
                      xlink:title="a"/>
              <person xlink:type="simple" xlink:href="/persons/b"
                      xlink:title="b" presence="absent"/>
              <person xlink:type="simple" xlink:href="/persons/c"
                      xlink:title="c" presence="present"/>
              <person xlink:type="simple" xlink:href="/persons/d"
                      xlink:title="d" presence="absent"/>
            </rollcall>""",
            "Bad presence value for /persons/a")
        self.post_errors("""
            <rollcall xmlns:xlink="http://www.w3.org/1999/xlink"
                      xlink:type="simple" xlink:title="group"
                      xlink:href="/groups/root"
                      datetime="2001-02-03 04:05:06">
              <reporter xlink:type="simple" xlink:href="/persons/a" />
              <comment>A comment</comment>
              <person xlink:type="simple" xlink:href="/persons/a"
                      xlink:title="a" presence="present"/>
              <person xlink:type="simple" xlink:href="/persons/b"
                      xlink:title="b" presence="absent" resolved="xyzzy"/>
              <person xlink:type="simple" xlink:href="/persons/c"
                      xlink:title="c" presence="present"/>
              <person xlink:type="simple" xlink:href="/persons/d"
                      xlink:title="d" presence="absent"/>
            </rollcall>""",
            "Bad resolved value for /persons/b")

    def test_post_logic_errors(self):
        self.post_errors("""
            <rollcall xmlns:xlink="http://www.w3.org/1999/xlink"
                      xlink:type="simple" xlink:title="group"
                      xlink:href="/groups/root"
                      datetime="2001-02-03 04:05:06">
              <reporter xlink:type="simple" xlink:href="/persons/x" />
              <comment>A comment</comment>
              <person xlink:type="simple" xlink:href="/persons/a"
                      xlink:title="a" presence="present"/>
              <person xlink:type="simple" xlink:href="/persons/b"
                      xlink:title="b" presence="absent"/>
              <person xlink:type="simple" xlink:href="/persons/c"
                      xlink:title="c" presence="present"/>
              <person xlink:type="simple" xlink:href="/persons/d"
                      xlink:title="d" presence="absent"/>
            </rollcall>""",
            "Reporter not found: /persons/x")
        self.post_errors("""
            <rollcall xmlns:xlink="http://www.w3.org/1999/xlink"
                      xlink:type="simple" xlink:title="group"
                      xlink:href="/groups/root"
                      datetime="2001-02-03 04:05:06">
              <reporter xlink:type="simple" xlink:href="/persons/a" />
              <comment>A comment</comment>
              <person xlink:type="simple" xlink:href="/persons/a"
                      xlink:title="a" presence="present"/>
              <person xlink:type="simple" xlink:href="/persons/a"
                      xlink:title="a" presence="present"/>
              <person xlink:type="simple" xlink:href="/persons/b"
                      xlink:title="b" presence="absent"/>
              <person xlink:type="simple" xlink:href="/persons/c"
                      xlink:title="c" presence="present"/>
              <person xlink:type="simple" xlink:href="/persons/d"
                      xlink:title="d" presence="absent"/>
            </rollcall>""",
            "Person mentioned more than once: /persons/a")
        self.post_errors("""
            <rollcall xmlns:xlink="http://www.w3.org/1999/xlink"
                      xlink:type="simple" xlink:title="group"
                      xlink:href="/groups/root"
                      datetime="2001-02-03 04:05:06">
              <reporter xlink:type="simple" xlink:href="/persons/a" />
              <comment>A comment</comment>
              <person xlink:type="simple" xlink:href="/persons/a"
                      xlink:title="a" presence="present"/>
              <person xlink:type="simple" xlink:href="/persons/b"
                      xlink:title="b" presence="absent"/>
              <person xlink:type="simple" xlink:href="/persons/c"
                      xlink:title="c" presence="present"/>
              <person xlink:type="simple" xlink:href="/persons/d"
                      xlink:title="d" presence="absent"/>
              <person xlink:type="simple" xlink:href="/persons/q"
                      xlink:title="q" presence="present"/>
            </rollcall>""",
            "Person /persons/q is not a member of /groups/root")
        self.post_errors("""
            <rollcall xmlns:xlink="http://www.w3.org/1999/xlink"
                      xlink:type="simple" xlink:title="group"
                      xlink:href="/groups/root"
                      datetime="2001-02-03 04:05:06">
              <reporter xlink:type="simple" xlink:href="/persons/a" />
              <comment>A comment</comment>
              <person xlink:type="simple" xlink:href="/persons/b"
                      xlink:title="b" presence="absent"/>
              <person xlink:type="simple" xlink:href="/persons/d"
                      xlink:title="d" presence="absent"/>
            </rollcall>""",
            "Persons not mentioned: /persons/a, /persons/c")
        self.post_errors("""
            <rollcall xmlns:xlink="http://www.w3.org/1999/xlink"
                      xlink:type="simple" xlink:title="group"
                      xlink:href="/groups/root"
                      datetime="2001-02-03 04:05:06">
              <reporter xlink:type="simple" xlink:href="/persons/a" />
              <comment>A comment</comment>
              <person xlink:type="simple" xlink:href="/persons/a"
                      xlink:title="a" presence="present"/>
              <person xlink:type="simple" xlink:href="/persons/b"
                      xlink:title="b" presence="absent" resolved="resolved"/>
              <person xlink:type="simple" xlink:href="/persons/c"
                      xlink:title="c" presence="present"/>
              <person xlink:type="simple" xlink:href="/persons/d"
                      xlink:title="d" presence="absent"/>
            </rollcall>""",
            "Cannot resolve an absence for absent person /persons/b")


class TestAbsenceTrackerView(XMLCompareMixin, RegistriesSetupMixin,
                             unittest.TestCase):

    def setUp(self):
        from schooltool.model import Person, AbsenceTrackerUtility
        from schooltool.model import AbsenceComment
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.views.model import AbsenceTrackerView
        from schooltool.interfaces import IAttendanceEvent
        self.setUpRegistries()
        app = Application()
        self.tracker = AbsenceTrackerUtility()
        app.utilityService['absences'] = self.tracker
        app.eventService.subscribe(self.tracker, IAttendanceEvent)
        app['persons'] = ApplicationObjectContainer(Person)
        self.person = app['persons'].new("a", title="a")
        dt = datetime.datetime(2001, 2, 3, 4, 5, 6)
        self.person.reportAbsence(AbsenceComment(dt=dt))
        self.view = AbsenceTrackerView(self.tracker)

    def test_get(self):
        request = RequestStub("http://localhost/utils/absences/")
        result = self.view.render(request)
        self.assertEquals(request.headers['Content-Type'],
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result, """
            <absences xmlns:xlink="http://www.w3.org/1999/xlink">
              <absence xlink:type="simple"
                       xlink:href="/persons/a/absences/001"
                       person_title="a"
                       datetime="2001-02-03 04:05:06"
                       ended="unended" xlink:title="001"
                       resolved="unresolved"/>
            </absences>
            """)


class TestAbsenceTrackerTextView(XMLCompareMixin, RegistriesSetupMixin,
                                 unittest.TestCase):

    def test_get_text_choice(self):
        from schooltool.views.model import AbsenceTrackerView
        context = AbsenceTrackerStub()
        view = AbsenceTrackerView(context)
        request = RequestStub("http://localhost/utils/absences/")
        request.accept = [(1, 'text/plain', {}, {}),
                          (0.5, 'text/html', {}, {})]
        result = view.render(request)
        self.assertEquals(request.headers['Content-Type'],
                          "text/plain; charset=UTF-8")

        request.accept = [(0.1, 'text/plain', {}, {}),
                          (0.5, 'text/xml', {}, {})]
        result = view.render(request)
        self.assertEquals(request.headers['Content-Type'],
                          "text/xml; charset=UTF-8")

        request.accept = [(0, 'text/plain', {}, {})]
        result = view.render(request)
        self.assertEquals(request.headers['Content-Type'],
                          "text/xml; charset=UTF-8")

    def test_get_text(self):
        from schooltool.model import Person, AbsenceTrackerUtility
        from schooltool.model import AbsenceComment
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.views.model import AbsenceTrackerView
        from schooltool.interfaces import IAttendanceEvent
        app = Application()
        self.tracker = AbsenceTrackerUtility()
        app.utilityService['absences'] = self.tracker
        app.eventService.subscribe(self.tracker, IAttendanceEvent)
        self.persons = app['persons'] = ApplicationObjectContainer(Person)
        self.view = AbsenceTrackerView(self.tracker)
        self.view.utcnow = lambda: datetime.datetime(2003, 11, 3, 12, 35)

        request = RequestStub("http://localhost/utils/absences/")
        request.accept = [('1', 'text/plain', {}, {})]
        result = self.view.render(request)
        self.assertEquals(request.headers['Content-Type'],
                          "text/plain; charset=UTF-8")

        steve = self.persons.new('steve', title='Steve Alexander')
        marius = self.persons.new('marius', title='Marius Gedminas')
        aiste = self.persons.new('aiste', title='Aiste Kesminaite')
        albert = self.persons.new('albert', title='Albertas Agejevas')
        vika = self.persons.new('vika', title='Viktorija Zaksiene')

        expected = dedent("""
            Absences at 12:35pm 2003-11-03 UTC
            ==================================

            Unexpected absences
            -------------------

            None

            Expected absences
            -----------------

            None
            """)
        self.assertEquals(result, expected, "\n" + diff(expected, result))

        dt = datetime.datetime(2003, 11, 3, 10, 0, 0)
        albert.reportAbsence(AbsenceComment(dt=dt))

        exp = datetime.datetime(2003, 11, 3, 13, 40, 0)
        dt = datetime.datetime(2003, 11, 3, 9, 0, 0)
        aiste.reportAbsence(AbsenceComment(dt=dt, expected_presence=exp,
                                           text='chiropodist appointment'))

        exp = datetime.datetime(2003, 11, 3, 10, 5, 0)
        dt = datetime.datetime(2003, 11, 3, 9, 0, 0)
        marius.reportAbsence(AbsenceComment(dt=dt, expected_presence=exp,
                                           text='dentist'))

        exp = datetime.datetime(2003, 11, 2, 11, 35, 0)
        dt = datetime.datetime(2003, 11, 2, 9, 0, 0)
        steve.reportAbsence(AbsenceComment(dt=dt, expected_presence=exp))

        exp = datetime.datetime(2003, 11, 4, 9, 0, 0)
        dt = datetime.datetime(2003, 11, 1, 9, 0, 0)
        vika.reportAbsence(AbsenceComment(dt=dt, expected_presence=exp,
                                          text='vacation'))
        result = self.view.render(request)
        expected = dedent(r"""
            Absences at 12:35pm 2003-11-03 UTC
            ==================================

            Unexpected absences
            -------------------

            Steve Alexander expected 25h0m ago, at 11:35am 2003-11-02
            Albertas Agejevas absent for 2h35m, since 10:00am today
            Marius Gedminas expected 2h30m ago, at 10:05am today (dentist)

            Expected absences
            -----------------

            Aiste Kesminaite expected in 1h5m, at 01:40pm today \
            (chiropodist appointment)
            Viktorija Zaksiene expected in 20h25m, at 09:00am 2003-11-04 \
            (vacation)
            """).replace("\\\n", "")
        self.assertEquals(result, expected, "\n" + diff(expected, result))


class TestAbsenceTrackerFacetView(TestAbsenceTrackerView):

    def setUp(self):
        from schooltool.model import Person, AbsenceTrackerFacet
        from schooltool.model import AbsenceComment
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.views.model import AbsenceTrackerFacetView
        from schooltool.facet import FacetManager

        self.setUpRegistries()
        app = Application()
        app['persons'] = ApplicationObjectContainer(Person)
        self.person = app['persons'].new("a", title="a")

        self.facet = AbsenceTrackerFacet()
        FacetManager(self.person).setFacet(self.facet)

        dt = datetime.datetime(2001, 2, 3, 4, 5, 6)
        self.person.reportAbsence(AbsenceComment(dt=dt))
        self.view = AbsenceTrackerFacetView(self.facet)

    def testDelete(self):
        request = RequestStub("http://localhost/persons/a/facets/001",
                              method="DELETE")
        result = self.view.render(request)
        expected = "Facet removed"
        self.assertEquals(result, expected, "\n" + diff(expected, result))


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestApplicationObjectTraverserView))
    suite.addTest(unittest.makeSuite(TestGroupView))
    suite.addTest(unittest.makeSuite(TestTreeView))
    suite.addTest(unittest.makeSuite(TestRollcallView))
    suite.addTest(unittest.makeSuite(TestPersonView))
    suite.addTest(unittest.makeSuite(TestAbsenceCommentParser))
    suite.addTest(unittest.makeSuite(TestAbsenceManagementView))
    suite.addTest(unittest.makeSuite(TestAbsenceView))
    suite.addTest(unittest.makeSuite(TestAbsenceTrackerView))
    suite.addTest(unittest.makeSuite(TestAbsenceTrackerTextView))
    suite.addTest(unittest.makeSuite(TestAbsenceTrackerFacetView))
    return suite

if __name__ == '__main__':
    unittest.main()
