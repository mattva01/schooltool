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
The views for the schooltool.absence objects.

$Id$
"""

import sets
import datetime
import libxml2
from zope.interface import moduleProvides
from schooltool.interfaces import IModuleSetup
from schooltool.interfaces import IGroup, IPerson
from schooltool.interfaces import IAbsenceTrackerUtility, IAbsenceTrackerFacet
from schooltool.interfaces import Unchanged
from schooltool.uris import URIMember
from schooltool.component import registerView
from schooltool.component import getPath, traverse
from schooltool.component import getRelatedObjects
from schooltool.absence import AbsenceComment
from schooltool.views import View, Template
from schooltool.views import read_file
from schooltool.views import absoluteURL, textErrorPage
from schooltool.views.facet import FacetView
from schooltool.views.auth import TeacherAccess, isManager
from schooltool.common import parse_datetime, to_unicode
from schooltool.schema.rng import validate_against_schema
from schooltool.translation import ugettext as _

__metaclass__ = type

moduleProvides(IModuleSetup)


class RollCallView(View):
    """This is a view for doing roll calls on groups."""

    template = Template('www/rollcall.pt', content_type="text/xml")
    authorization = TeacherAccess

    def groupPath(self):
        return getPath(self.context)

    def listPersons(self, group=None, _already_added=None):
        if group is None:
            group = self.context
        if _already_added is None:
            _already_added = sets.Set()
        results = []
        for member in getRelatedObjects(group, URIMember):
            if (IPerson.providedBy(member)
                and member not in _already_added):
                absence = member.getCurrentAbsence()
                if absence is None:
                    presence = "present"
                    expected_presence = None
                else:
                    presence = "absent"
                    expected_presence = absence.expected_presence
                    if expected_presence:
                        expected_presence = expected_presence.isoformat(' ')
                _already_added.add(member)
                results.append({'title': member.title, 'href': getPath(member),
                                'presence': presence,
                                'expected_presence': expected_presence})
            if IGroup.providedBy(member):
                results.extend(self.listPersons(member, _already_added))
        return results

    def parseRollcall(self, request):
        """Parse roll call document.

        Returns (datetime, reporter, comment_text, items) where items is a list
        of (person, present).
        """
        body = request.content.read()
        try:
            doc = libxml2.parseDoc(body)
        except libxml2.parserError:
            raise ValueError("Bad roll call representation")
        ctx = doc.xpathNewContext()
        xlink = "http://www.w3.org/1999/xlink"
        try:
            ctx.xpathRegisterNs("xlink", xlink)

            res = ctx.xpathEval("/rollcall/@datetime")
            if res:
                dt = parse_datetime(to_unicode(res[0].content))
            else:
                dt = None

            res = ctx.xpathEval("/rollcall/reporter/@xlink:href")
            if not res:
                reporter = request.authenticated_user
            else:
                path = to_unicode(res[0].content)
                try:
                    reporter = traverse(self.context, path)
                except KeyError:
                    raise ValueError("Reporter not found: %s" % path)
                if (reporter is not request.authenticated_user
                        and not isManager(request.authenticated_user)):
                    raise ValueError("Reporter does not match the"
                                     " authenticated user")

            items = []
            presence = {'present': True, 'absent': False}
            resolvedness = {None: Unchanged, 'resolved': True,
                            'unresolved': False}
            seen = sets.Set()
            members = sets.Set([item['href'] for item in self.listPersons()])
            for node in ctx.xpathEval("/rollcall/person"):
                path = to_unicode(node.nsProp('href', xlink))
                if path is None:
                    raise ValueError("Person does not specify xlink:href")
                if path in seen:
                    raise ValueError("Person mentioned more than once: %s"
                                     % path)
                seen.add(path)
                if path not in members:
                    raise ValueError("Person %s is not a member of %s"
                                     % (path, getPath(self.context)))
                person = traverse(self.context, path)
                try:
                    presence_attr = to_unicode(node.nsProp('presence', None))
                    present = presence[presence_attr]
                except KeyError:
                    raise ValueError("Bad presence value for %s" % path)
                try:
                    resolved_attr = to_unicode(node.nsProp('resolved', None))
                    resolved = resolvedness[resolved_attr]
                except KeyError:
                    raise ValueError("Bad resolved value for %s" % path)
                if resolved is True and not present:
                    raise ValueError("Cannot resolve an absence for absent"
                                     " person %s" % path)
                text = to_unicode(node.nsProp('comment', None))
                items.append((person, present, resolved, text))
            if seen != members:
                missing = list(members - seen)
                missing.sort()
                raise ValueError("Persons not mentioned: %s"
                                 % ', '.join(missing))
            return dt, reporter, items
        finally:
            doc.freeDoc()
            ctx.xpathFreeContext()

    def do_POST(self, request):
        request.setHeader('Content-Type', 'text/plain')
        nabsences = npresences = 0
        try:
            dt, reporter, items = self.parseRollcall(request)
        except ValueError, e:
            return textErrorPage(request, str(e))
        for person, present, resolved, text in items:
            if not present:
                person.reportAbsence(AbsenceComment(reporter, text, dt=dt,
                                                    absent_from=self.context))
                nabsences += 1
            if present and person.getCurrentAbsence() is not None:
                person.reportAbsence(AbsenceComment(reporter, text, dt=dt,
                                                    absent_from=self.context,
                                                    ended=True,
                                                    resolved=resolved))
                npresences += 1
        return (_("%d absences and %d presences reported")
                % (nabsences, npresences))


class AbsenceCommentParser:

    schema = read_file("../schema/absencecomment.rng")

    def parseComment(self, request):
        """Parse and create an AbsenceComment from a given request body"""
        body = request.content.read()

        try:
            if not validate_against_schema(self.schema, body):
                raise ValueError("Document not valid according to schema")
        except libxml2.parserError:
            raise ValueError("Document not valid XML")

        doc = libxml2.parseDoc(body)
        xpathctx = doc.xpathNewContext()
        try:
            ns = 'http://schooltool.org/ns/model/0.1'
            xpathctx.xpathRegisterNs('m', ns)
            node = xpathctx.xpathEval('/m:absencecomment')[0]

            text = to_unicode(node.nsProp('text', None))
            if text is None:
                raise ValueError("Text attribute missing")

            reporter_path = to_unicode(node.nsProp('reporter', None))
            if reporter_path is None:
                raise ValueError("Reporter attribute missing")

            try:
                reporter = traverse(self.context, reporter_path)
            except KeyError:
                raise ValueError("Reporter not found: %s" % reporter_path)

            dt = to_unicode(node.nsProp('datetime', None))
            if dt is not None:
                dt = parse_datetime(dt)

            absent_from_path = to_unicode(node.nsProp('absent_from', None))
            if absent_from_path is not None:
                try:
                    absent_from = traverse(self.context, absent_from_path)
                except KeyError:
                    raise ValueError("Object not found: %s" % reporter_path)
            else:
                absent_from = None

            ended = to_unicode(node.nsProp('ended', None))
            if ended is None:
                ended = Unchanged
            else:
                d = {'ended': True, 'unended': False}
                if ended not in d:
                    raise ValueError("Bad value for ended", ended)
                ended = d[ended]

            resolved = to_unicode(node.nsProp('resolved', None))
            if resolved is None:
                resolved = Unchanged
            else:
                d = {'resolved': True, 'unresolved': False}
                if resolved not in d:
                    raise ValueError("Bad value for resolved", resolved)
                resolved = d[resolved]

            expected_presence = to_unicode(node.nsProp('expected_presence',
                                                       None))
            if expected_presence is None:
                expected_presence = Unchanged
            else:
                if expected_presence == '':
                    expected_presence = None
                else:
                    expected_presence = parse_datetime(expected_presence)
        finally:
            doc.freeDoc()
            xpathctx.xpathFreeContext()

        comment = AbsenceComment(reporter, text, absent_from=absent_from,
                                 dt=dt, ended=ended, resolved=resolved,
                                 expected_presence=expected_presence)

        return comment


class AbsenceListViewMixin:

    def _listAbsences(self, absences, titles):
        endedness = {False: 'unended', True: 'ended'}
        resolvedness = {False: 'unresolved', True: 'resolved'}
        person_title = None
        for absence in absences:
            expected_presence = None
            if absence.expected_presence is not None:
                expected_presence = absence.expected_presence.isoformat(' ')
            if titles:
                person_title = absence.person.title
            yield {'title': absence.__name__,
                   'path': getPath(absence),
                   'person_title': person_title,
                   'datetime': absence.comments[0].datetime.isoformat(' '),
                   'expected_presence': expected_presence,
                   'ended': endedness[absence.ended],
                   'resolved': resolvedness[absence.resolved],
                   'last_comment': absence.comments[-1].text}


class AbsenceManagementView(View, AbsenceCommentParser, AbsenceListViewMixin):

    template = Template('www/absences.pt', content_type="text/xml")
    authorization = TeacherAccess

    def _traverse(self, name, request):
        absence = self.context.getAbsence(name)
        return AbsenceView(absence)

    def listAbsences(self):
        return self._listAbsences(self.context.iterAbsences(), False)

    def do_POST(self, request):
        try:
            comment = self.parseComment(request)
        except ValueError, e:
            return textErrorPage(request, str(e))
        absence = self.context.reportAbsence(comment)
        location = absoluteURL(request, getPath(absence))
        request.setHeader('Location', location)
        request.setHeader('Content-Type', 'text/plain')
        if len(absence.comments) == 1:
            request.setResponseCode(201, 'Created')
            return _("Absence created: %s") % getPath(absence)
        else:
            request.setResponseCode(200, 'OK')
            return _("Absence updated: %s") % getPath(absence)


class AbsenceView(View, AbsenceCommentParser):

    template = Template('www/absence.pt', content_type="text/xml")
    authorization = TeacherAccess

    def ended(self):
        if self.context.ended:
            return "ended"
        else:
            return "unended"

    def resolved(self):
        if self.context.resolved:
            return "resolved"
        else:
            return "unresolved"

    def expected_presence(self):
        if self.context.expected_presence:
            return self.context.expected_presence.isoformat(' ')
        else:
            return None

    def person_href(self):
        return getPath(self.context.person)

    def person_title(self):
        return self.context.person.title

    def listComments(self):
        endedness = {Unchanged: None, False: 'unended', True: 'ended'}
        resolvedness = {Unchanged: None, False: 'unresolved', True: 'resolved'}
        for comment in self.context.comments:
            absent_from_title = absent_from_href = None
            if comment.absent_from is not None:
                absent_from_href = getPath(comment.absent_from)
                absent_from_title = comment.absent_from.title
            if comment.expected_presence is Unchanged:
                expected_presence = None
            elif comment.expected_presence is None:
                expected_presence = ''
            else:
                expected_presence = comment.expected_presence.isoformat(' ')
            yield {'datetime': comment.datetime.isoformat(' '),
                   'text': comment.text,
                   'reporter_title': comment.reporter.title,
                   'reporter_href': getPath(comment.reporter),
                   'absent_from_title': absent_from_title,
                   'absent_from_href': absent_from_href,
                   'ended': endedness[comment.ended],
                   'resolved': resolvedness[comment.resolved],
                   'expected_presence': expected_presence}

    def do_POST(self, request):
        try:
            comment = self.parseComment(request)
        except ValueError, e:
            return textErrorPage(request, str(e))
        try:
            self.context.addComment(comment)
        except ValueError:
            return textErrorPage(request, _("Cannot reopen an absence"
                                            " when another one is not ended"))
        request.setHeader('Content-Type', 'text/plain')
        return _("Comment added")


class AbsenceTrackerView(View, AbsenceListViewMixin):

    template = Template('www/absences.pt', content_type='text/xml')
    authorization = TeacherAccess

    utcnow = datetime.datetime.utcnow

    def format_reason(self, reason):
        if reason is None:
            return ''
        else:
            return ' (%s)' % reason

    def format_date(self, date, now):
        if date.date() == now.date():
            return _('today')
        else:
            return date.strftime('%Y-%m-%d')

    def text_template(self, request):
        request.setHeader('Content-Type', 'text/plain; charset=UTF-8')
        result = []
        now = self.utcnow()
        format_reason = self.format_reason
        format_date = self.format_date
        header = _("Absences at %s") % (now.strftime("%H:%M%p %Y-%m-%d UTC"))
        result.append("%s\n%s\n" % (header, "=" * len(header)))
        unexp = _("Unexpected absences")
        result.append(unexp)
        result.append("-" * len(unexp) + "\n")
        unexpected = self.unexpected(now)
        if not unexpected:
            result.append(_("None"))
        else:
            for absence in unexpected:
                if absence.expected_presence:
                    when_expected = absence.expected_presence
                    age = now - when_expected
                    seconds_in_day = 86400
                    agestring = _('%dh%dm') % divmod(
                        (age.days * seconds_in_day + age.seconds) / 60, 60)
                    reason = absence.comments[-1].text
                    result.append(_("%s expected %s ago, at %s %s%s") %
                                  (absence.person.title,
                                   agestring,
                                   when_expected.strftime("%I:%M%p"),
                                   format_date(when_expected, now),
                                   format_reason(reason)
                                   ))
                else:
                    start = absence.comments[0].datetime
                    age = now - start
                    seconds_in_day = 86400
                    agestring = _('%dh%dm') % divmod(
                        (age.days * seconds_in_day + age.seconds) / 60, 60)
                    reason = absence.comments[-1].text
                    result.append(_("%s absent for %s, since %s %s%s") %
                                  (absence.person.title,
                                   agestring,
                                   start.strftime("%I:%M%p"),
                                   format_date(start, now),
                                   format_reason(reason)
                                   ))
        result.append("")
        exp = _("Expected absences")
        result.append(exp)
        result.append('-' * len(exp) + "\n")
        expected = self.expected(now)
        if not expected:
            result.append(_("None"))
        else:
            for absence in expected:
                when_expected = absence.expected_presence
                age = when_expected - now
                seconds_in_day = 86400
                agestring = '%dh%dm' % divmod(
                    (age.days * seconds_in_day + age.seconds) / 60, 60)
                reason = absence.comments[-1].text
                result.append(_("%s expected in %s, at %s %s%s") %
                              (absence.person.title,
                               agestring,
                               when_expected.strftime("%I:%M%p"),
                               format_date(when_expected, now),
                               format_reason(reason)
                               ))
        result.append("")
        return "\n".join(result)

    def unexpected(self, now):
        L = [(absence.expected_presence or absence.comments[0].datetime,
              absence)
             for absence in self.context.absences
             if absence.expected_presence is None or
             absence.expected_presence < now]
        L.sort()
        return [absence for sortkey, absence in L]

    def expected(self, now):
        L = [(absence.expected_presence, absence)
             for absence in self.context.absences
             if absence.expected_presence is not None and
             absence.expected_presence >= now]
        L.sort()
        return [absence for sortkey, absence in L]

    def listAbsences(self):
        return self._listAbsences(self.context.absences, True)

    def do_GET(self, request):
        mtype = request.chooseMediaType(['text/xml', 'text/plain'])
        if mtype == 'text/plain':
            return self.text_template(request)
        else:
            return self.template(request, view=self, context=self.context)


class AbsenceTrackerFacetView(AbsenceTrackerView, FacetView):
    pass


#
# Setup
#

def setUp():
    """See IModuleSetup."""
    registerView(IAbsenceTrackerUtility, AbsenceTrackerView)
    registerView(IAbsenceTrackerFacet, AbsenceTrackerFacetView)

