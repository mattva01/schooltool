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
Unit tests for schooltool.views.absence

$Id$
"""

import datetime
from logging import INFO
import unittest
from schooltool.tests.utils import RegistriesSetupMixin, EventServiceTestMixin
from schooltool.tests.utils import XMLCompareMixin
from schooltool.tests.utils import QuietLibxml2Mixin
from schooltool.tests.helpers import diff, dedent
from schooltool.views.tests import RequestStub
from schooltool.views.tests import TraversableStub, TraversableRoot, setPath

__metaclass__ = type


class AbsenceTrackerStub:

    def __init__(self):
        self.absences = []


class TestAbsenceCommentParser(QuietLibxml2Mixin, unittest.TestCase):

    def setUp(self):
        self.setUpLibxml2()

    def tearDown(self):
        self.tearDownLibxml2()

    def test_parseComment(self):
        from schooltool.interfaces import Unchanged
        from schooltool.views.absence import AbsenceCommentParser
        john = object()
        group = object()
        persons = TraversableStub(john=john)
        groups = TraversableStub(aa=group)
        root = TraversableRoot(persons=persons, groups=groups)
        parser = AbsenceCommentParser()
        parser.context = root

        # The very minimum
        request = RequestStub(body="""
            <absencecomment xmlns="http://schooltool.org/ns/model/0.1"
                        text="Foo \xe2\x9c\xb0"
                        reporter="/persons/john"
                        />
                    """)
        lower_limit = datetime.datetime.utcnow()
        comment = parser.parseComment(request)
        upper_limit = datetime.datetime.utcnow()
        self.assertEquals(comment.text, u"Foo \u2730")
        self.assertEquals(comment.reporter, john)
        self.assert_(lower_limit <= comment.datetime <= upper_limit)
        self.assert_(comment.absent_from is None)
        self.assert_(comment.ended is Unchanged)
        self.assert_(comment.resolved is Unchanged)
        self.assert_(comment.expected_presence is Unchanged)

        # Everything
        request = RequestStub(body="""
            <absencecomment xmlns="http://schooltool.org/ns/model/0.1"
                        text="Foo \xe2\x9c\xb0"
                        reporter="/persons/john"
                        absent_from="/groups/aa"
                        ended="ended"
                        resolved="unresolved"
                        datetime="2004-04-04 04:04:04"
                        expected_presence="2005-05-05 05:05:05" />
                    """)
        comment = parser.parseComment(request)
        self.assertEquals(comment.text, u"Foo \u2730")
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
            <absencecomment xmlns="http://schooltool.org/ns/model/0.1"
                        text="Foo"
                        reporter="/persons/john"
                        expected_presence=""
                        />
                    """)
        comment = parser.parseComment(request)
        self.assert_(comment.expected_presence is None)

    def test_parseComment_errors(self):
        from schooltool.views.absence import AbsenceCommentParser
        parser = AbsenceCommentParser()
        parser.context = TraversableRoot(obj=object())
        bad_requests = (
            '',
            '<absencecomment xmlns="http://schooltool.org/ns/model/0.1"'
            ' reporter="/obj"/>',
            '<absencecomment xmlns="http://schooltool.org/ns/model/0.1"'
            ' text=""/>',
            '<absencecomment xmlns="http://schooltool.org/ns/model/0.1"'
            ' text="" reporter="/does/not/exist"/>',
            '<absencecomment xmlns="http://schooltool.org/ns/model/0.1"'
            ' text="" reporter="/obj" datetime="now"/>',
            '<absencecomment xmlns="http://schooltool.org/ns/model/0.1"'
            ' text="" reporter="/obj" absent_from="/does/not/exist"/>',
            '<absencecomment xmlns="http://schooltool.org/ns/model/0.1"'
            ' text="" reporter="/obj" ended="mu"/>',
            '<absencecomment xmlns="http://schooltool.org/ns/model/0.1"'
            ' text="" reporter="/obj" resolved="mu"/>',
            '<absencecomment xmlns="http://schooltool.org/ns/model/0.1"'
            ' text="" reporter="/obj" expected_presence="dunno"/>',
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

    def setUp(self):
        self.setUpEventService()

    def test_traverse(self):
        from schooltool.views.absence import AbsenceManagementView, AbsenceView
        from schooltool.model import Person
        from schooltool.absence import AbsenceComment
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
        from schooltool.model import Person
        from schooltool.absence import AbsenceComment
        context = Person()
        setPath(context, '/person', root=self.serviceManager)
        dt = datetime.datetime(2001, 2, 3, 4, 5, 6)
        context.reportAbsence(AbsenceComment(dt=dt, ended=True, resolved=True))
        context.reportAbsence(AbsenceComment(dt=dt))
        self.assertEquals(len(list(context.iterAbsences())), 2)
        view = AbsenceManagementView(context)
        request = RequestStub("http://localhost/person/absences")
        view.authorization = lambda ctx, rq: True
        result = view.render(request)
        self.assertEquals(request.headers['content-type'],
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
        context.title = 'Mr. Foo'
        setPath(context, '/person', root=self.serviceManager)
        basepath = "/person/absences/"
        baseurl = "http://localhost:7001%s" % basepath
        view = AbsenceManagementView(context)
        xml = '''<absencecomment xmlns="http://schooltool.org/ns/model/0.1"
                     text="Foo" reporter="." />'''
        request = RequestStub(baseurl[:-1], method="POST", body=xml)

        view.authorization = lambda ctx, rq: True

        result = view.render(request)

        self.assertEquals(request.code, 201)
        self.assertEquals(request.reason, "Created")
        self.assertEquals(request.applog,
                [(None, 'Absence /person/absences/001 of Mr. Foo created',
                  INFO)])
        location = request.headers['location']
        self.assert_(location.startswith(baseurl),
                     "%r.startswith(%r) failed" % (location, baseurl))
        name = location[len(baseurl):]
        self.assertEquals(request.headers['content-type'],
                          "text/plain; charset=UTF-8")
        path = '%s%s' % (basepath, name)
        self.assert_(path in result, '%r not in %r' % (path, result))
        self.assertEquals(len(list(context.iterAbsences())), 1)
        absence = context.getAbsence(name)
        comment = absence.comments[0]
        self.assertEquals(comment.text, "Foo")

    def test_post_another_one(self):
        from schooltool.views.model import AbsenceManagementView
        from schooltool.model import Person
        from schooltool.absence import AbsenceComment
        context = Person()
        context.title = 'Mr. Foo'
        setPath(context, '/person', root=self.serviceManager)
        absence = context.reportAbsence(AbsenceComment())
        basepath = "/person/absences/"
        baseurl = "http://localhost:7001%s" % basepath
        view = AbsenceManagementView(context)

        xml = '''<absencecomment xmlns="http://schooltool.org/ns/model/0.1"
                     text="Bar" reporter="." />'''
        request = RequestStub(baseurl[:-1], method="POST", body=xml)

        view.authorization = lambda ctx, rq: True
        result = view.render(request)

        self.assertEquals(request.applog,
                [(None, 'Absence /person/absences/001 of Mr. Foo updated',
                  INFO)])
        self.assertEquals(request.code, 200)
        self.assertEquals(request.reason, "OK")
        location = request.headers['location']
        self.assert_(location.startswith(baseurl),
                     "%r.startswith(%r) failed" % (location, baseurl))
        name = location[len(baseurl):]
        self.assertEquals(request.headers['content-type'],
                          "text/plain; charset=UTF-8")
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
        self.assertEquals(request.applog, [])

        view.authorization = lambda ctx, rq: True
        result = view.render(request)

        self.assertEquals(request.code, 400)
        self.assertEquals(request.reason, "Bad Request")
        self.assertEquals(request.headers['content-type'],
                          "text/plain; charset=UTF-8")
        self.assertEquals(request.applog, [])
        self.assertEquals(result, "Document not valid XML")


class TestAbsenceView(XMLCompareMixin, EventServiceTestMixin,
                      unittest.TestCase):

    def setUp(self):
        self.setUpEventService()

    def createAbsence(self):
        from schooltool.model import Person, Group
        from schooltool.absence import AbsenceComment
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
        from schooltool.views.absence import AbsenceView
        absence = self.createAbsence()
        view = AbsenceView(absence)
        request = RequestStub("http://localhost/person/absences/001")
        view.authorization = lambda ctx, rq: True
        result = view.render(request)
        self.assertEquals(request.headers['content-type'],
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
        from schooltool.views.absence import AbsenceView
        absence = self.createAbsence()
        view = AbsenceView(absence)
        basepath = "/person/absences/001/"
        baseurl = "http://localhost" + basepath
        body = '''<absencecomment xmlns="http://schooltool.org/ns/model/0.1"
                     text="Foo \xe2\x9c\xb0" reporter="." />'''
        request = RequestStub(baseurl[:-1], method="POST", body=body)
        view.authorization = lambda ctx, rq: True
        result = view.render(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(request.reason, "OK")
        self.assertEquals(request.headers['content-type'],
                          "text/plain; charset=UTF-8")
        self.assertEquals(request.applog,
                [(None, 'Comment for absence /person/absences/001 of A Person'
                        ' added', INFO)])
        self.assertEquals(result, "Comment added")
        comment = absence.comments[-1]
        self.assertEquals(comment.text, u"Foo \u2730")

    def test_post_errors(self):
        from schooltool.views.absence import AbsenceView
        absence = self.createAbsence()
        self.assertEquals(len(absence.comments), 2)
        basepath = "/person/absences/001/"
        setPath(absence, basepath[:-1])
        baseurl = "http://localhost" + basepath
        body = '''<absencecomment xmlns="http://schooltool.org/ns/model/0.1"
                     text="Foo" reporter="/does/not/exist" />'''
        request = RequestStub(baseurl[:-1], method="POST", body=body)
        view = AbsenceView(absence)
        view.authorization = lambda ctx, rq: True
        result = view.render(request)
        self.assertEquals(request.code, 400)
        self.assertEquals(request.reason, "Bad Request")
        self.assertEquals(request.headers['content-type'],
                          "text/plain; charset=UTF-8")
        self.assertEquals(request.applog, [])
        self.assertEquals(result, "Reporter not found: /does/not/exist")
        self.assertEquals(len(absence.comments), 2)

    def test_post_duplicate(self):
        from schooltool.views.absence import AbsenceView
        from schooltool.absence import AbsenceComment
        absence = self.createAbsence()
        absence.person.reportAbsence(AbsenceComment())
        self.assertEquals(len(absence.comments), 2)
        basepath = "/person/absences/001/"
        setPath(absence, basepath[:-1])
        baseurl = "http://localhost" + basepath
        body = '''<absencecomment xmlns="http://schooltool.org/ns/model/0.1"
                     text="Foo" reporter="." ended="unended"/>'''
        request = RequestStub(baseurl[:-1], method="POST", body=body)
        view = AbsenceView(absence)
        view.authorization = lambda ctx, rq: True
        result = view.render(request)
        self.assertEquals(request.code, 400)
        self.assertEquals(request.reason, "Bad Request")
        self.assertEquals(request.headers['content-type'],
                          "text/plain; charset=UTF-8")
        self.assertEquals(request.applog, [])
        self.assertEquals(result,
            "Cannot reopen an absence when another one has not ended")
        self.assertEquals(len(absence.comments), 2)


class TestRollCallView(XMLCompareMixin, RegistriesSetupMixin,
                       QuietLibxml2Mixin, unittest.TestCase):

    def setUp(self):
        from schooltool.model import Group, Person
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.membership import Membership
        from schooltool import membership
        self.setUpLibxml2()
        self.setUpRegistries()
        membership.setUp()
        app = Application()
        app['groups'] = ApplicationObjectContainer(Group)
        app['persons'] = ApplicationObjectContainer(Person)
        self.group = app['groups'].new("root", title="group")
        self.managers = app['groups'].new("managers", title="managers")
        self.sub = app['groups'].new("subgroup", title="subgroup")
        self.subsub = app['groups'].new("subsubgroup", title="subsubgroup")
        self.sub2 = app['groups'].new("subgroup2", title="subgroup")
        self.persona = app['persons'].new("a", title="a")
        self.personb = app['persons'].new("b", title="b")
        self.personc = app['persons'].new("c", title="c")
        self.persond = app['persons'].new("d", title="d")
        self.personq = app['persons'].new("q", title="q")
        self.manager = app['persons'].new("mgr", title="manager")

        Membership(group=self.group, member=self.sub)
        Membership(group=self.sub, member=self.subsub)
        Membership(group=self.group, member=self.persona)
        Membership(group=self.sub, member=self.personb)
        Membership(group=self.subsub, member=self.personc)
        Membership(group=self.subsub, member=self.persond)
        # a person can belong to more than one group
        Membership(group=self.subsub, member=self.persona)
        Membership(group=self.sub2, member=self.personb)

        Membership(group=self.managers, member=self.manager)

    def tearDown(self):
        self.tearDownRegistries()
        self.tearDownLibxml2()

    def test_get(self):
        from schooltool.views.absence import RollCallView
        from schooltool.absence import AbsenceComment
        self.personb.reportAbsence(AbsenceComment())
        self.personc.reportAbsence(AbsenceComment(None, "",
                expected_presence=datetime.datetime(2001, 1, 1, 2, 2, 2)))
        view = RollCallView(self.group)
        request = RequestStub("http://localhost/group/rollcall")
        view.authorization = lambda ctx, rq: True
        result = view.render(request)
        self.assertEquals(request.headers['content-type'],
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
        from schooltool.views.absence import RollCallView
        from schooltool.absence import AbsenceComment
        personc_absence = self.personc.reportAbsence(AbsenceComment())
        persond_absence = self.persond.reportAbsence(AbsenceComment())
        view = RollCallView(self.group)
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
            """ % text, authenticated_user=self.manager)
        view.authorization = lambda ctx, rq: True
        result = view.render(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(request.reason, "OK")
        self.assertEquals(request.headers['content-type'],
                          "text/plain; charset=UTF-8")
        self.assertEquals(result, "2 absences and 1 presences reported")

        self.assertEquals(request.applog,
                [(self.manager, msg, INFO)
                 for msg in
                        ['Absence /persons/b/absences/001 of b reported',
                         'Presence /persons/c/absences/001 of c reported',
                         'Absence /persons/d/absences/001 of d reported']])

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

    def test_post_no_reporter(self):
        from schooltool.views.absence import RollCallView
        view = RollCallView(self.group)
        view.authorization = lambda ctx, rq: True
        request = RequestStub("http://localhost/group/rollcall",
                              method="POST", body="""
            <rollcall xmlns:xlink="http://www.w3.org/1999/xlink"
                      xlink:type="simple" xlink:title="group"
                      xlink:href="/groups/root"
                      datetime="2001-02-03 04:05:06">
              <person xlink:type="simple" xlink:href="/persons/a"
                      xlink:title="a" presence="absent"/>
              <person xlink:type="simple" xlink:href="/persons/b"
                      xlink:title="b" presence="present"/>
              <person xlink:type="simple" xlink:href="/persons/c"
                      xlink:title="b" presence="absent"/>
              <person xlink:type="simple" xlink:href="/persons/d"
                      xlink:title="b" presence="absent"/>
            </rollcall>
            """, authenticated_user=self.personb)
        # when reporter is not explicitly specified, take authenticated_user
        result = view.render(request)
        self.assertEquals(request.applog,
                [(self.personb,
                  'Absence /persons/%s/absences/001 of %s reported' %
                  (person, person), INFO)
                 for person in ['a', 'c', 'd']])
        self.assertEquals(request.code, 200, 'request failed:\n' + result)
        absence = self.persona.getCurrentAbsence()
        comment = absence.comments[-1]
        self.assert_(comment.reporter is self.personb)

    def test_post_no_authorization(self):
        from schooltool.views.absence import RollCallView
        view = RollCallView(self.group)
        view.authorization = lambda ctx, rq: True
        request = RequestStub("http://localhost/group/rollcall",
                              method="POST", body="""
            <rollcall xmlns:xlink="http://www.w3.org/1999/xlink"
                      xlink:type="simple" xlink:title="group"
                      xlink:href="/groups/root"
                      datetime="2001-02-03 04:05:06">
              <reporter xlink:type="simple" xlink:href="/persons/a" />
              <person xlink:type="simple" xlink:href="/persons/a"
                      xlink:title="a" presence="absent"/>
              <person xlink:type="simple" xlink:href="/persons/b"
                      xlink:title="b" presence="present"/>
              <person xlink:type="simple" xlink:href="/persons/c"
                      xlink:title="b" presence="absent"/>
              <person xlink:type="simple" xlink:href="/persons/d"
                      xlink:title="b" presence="absent"/>
            </rollcall>
            """, authenticated_user=self.personb)
        # when reporter is not explicitly specified, take authenticated_user
        result = view.render(request)
        self.assertEquals(request.code, 400)
        self.assertEquals(request.reason, "Bad Request")
        self.assertEquals(request.headers['content-type'],
                          "text/plain; charset=UTF-8")
        self.assertEquals(request.applog, [])
        self.assertEquals(result, "Reporter does not match the authenticated"
                                  " user")

    def post_errors(self, body, errmsg):
        from schooltool.views.absence import RollCallView
        view = RollCallView(self.group)
        request = RequestStub("http://localhost/group/rollcall",
                              method="POST", body=body,
                              authenticated_user=self.manager)
        view.authorization = lambda ctx, rq: True
        result = view.render(request)
        self.assertEquals(request.code, 400)
        self.assertEquals(request.reason, "Bad Request")
        self.assertEquals(request.headers['content-type'],
                          "text/plain; charset=UTF-8")
        self.assertEquals(request.applog, [])
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
        from schooltool.model import Person
        from schooltool.absence import AbsenceComment, AbsenceTrackerUtility
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.views.absence import AbsenceTrackerView
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
        self.view.authorization = lambda ctx, rq: True

    def test_get(self):
        request = RequestStub("http://localhost/utils/absences/")
        result = self.view.render(request)
        self.assertEquals(request.headers['content-type'],
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
        from schooltool.views.absence import AbsenceTrackerView
        context = AbsenceTrackerStub()
        view = AbsenceTrackerView(context)
        request = RequestStub("http://localhost/utils/absences/")
        request.accept = [(1, 'text/plain', {}, {}),
                          (0.5, 'text/html', {}, {})]
        view.authorization = lambda ctx, rq: True
        result = view.render(request)
        self.assertEquals(request.headers['content-type'],
                          "text/plain; charset=UTF-8")

        request.accept = [(0.1, 'text/plain', {}, {}),
                          (0.5, 'text/xml', {}, {})]
        result = view.render(request)
        self.assertEquals(request.headers['content-type'],
                          "text/xml; charset=UTF-8")

        request.accept = [(0, 'text/plain', {}, {})]
        result = view.render(request)
        self.assertEquals(request.headers['content-type'],
                          "text/xml; charset=UTF-8")

    def test_get_text(self):
        from schooltool.model import Person
        from schooltool.absence import AbsenceComment, AbsenceTrackerUtility
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.views.absence import AbsenceTrackerView
        from schooltool.interfaces import IAttendanceEvent
        app = Application()
        self.tracker = AbsenceTrackerUtility()
        app.utilityService['absences'] = self.tracker
        app.eventService.subscribe(self.tracker, IAttendanceEvent)
        self.persons = app['persons'] = ApplicationObjectContainer(Person)
        view = AbsenceTrackerView(self.tracker)
        view.utcnow = lambda: datetime.datetime(2003, 11, 3, 12, 35)
        view.authorization = lambda ctx, rq: True

        request = RequestStub("http://localhost/utils/absences/")
        request.accept = [('1', 'text/plain', {}, {})]
        result = view.render(request)
        self.assertEquals(request.headers['content-type'],
                          "text/plain; charset=UTF-8")

        steve = self.persons.new('steve', title='Steve Alexander')
        marius = self.persons.new('marius', title='Marius Gedminas')
        aiste = self.persons.new('aiste', title='Aiste Kesminaite')
        albert = self.persons.new('albert', title='Albertas Agejevas')
        vika = self.persons.new('vika', title='Viktorija Zaksiene')

        expected = dedent("""
            Absences at 12:35PM 2003-11-03 UTC
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
        result = view.render(request)
        expected = dedent(r"""
            Absences at 12:35PM 2003-11-03 UTC
            ==================================

            Unexpected absences
            -------------------

            Steve Alexander expected 25h0m ago, at 11:35AM 2003-11-02
            Albertas Agejevas absent for 2h35m, since 10:00AM today
            Marius Gedminas expected 2h30m ago, at 10:05AM today (dentist)

            Expected absences
            -----------------

            Aiste Kesminaite expected in 1h5m, at 01:40PM today \
            (chiropodist appointment)
            Viktorija Zaksiene expected in 20h25m, at 09:00AM 2003-11-04 \
            (vacation)
            """).replace("\\\n", "")
        self.assertEquals(result, expected, "\n" + diff(expected, result))


class TestAbsenceTrackerFacetView(TestAbsenceTrackerView):

    def setUp(self):
        from schooltool.model import Person
        from schooltool.absence import AbsenceTrackerFacet, AbsenceComment
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.views.absence import AbsenceTrackerFacetView
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
        self.view.authorization = lambda ctx, rq: True

    def testDelete(self):
        request = RequestStub("http://localhost/persons/a/facets/001",
                              method="DELETE")
        result = self.view.render(request)
        expected = "Facet /persons/a/facets/001 (AbsenceTrackerFacet) removed"
        self.assertEquals(result, expected, "\n" + diff(expected, result))


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestAbsenceCommentParser))
    suite.addTest(unittest.makeSuite(TestAbsenceManagementView))
    suite.addTest(unittest.makeSuite(TestAbsenceView))
    suite.addTest(unittest.makeSuite(TestAbsenceTrackerView))
    suite.addTest(unittest.makeSuite(TestAbsenceTrackerTextView))
    suite.addTest(unittest.makeSuite(TestAbsenceTrackerFacetView))
    suite.addTest(unittest.makeSuite(TestRollCallView))
    return suite

if __name__ == '__main__':
    unittest.main()
