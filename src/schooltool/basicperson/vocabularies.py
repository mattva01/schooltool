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
Sources and vocabularies for form fields.

$Id$

"""
from zope.interface import implements
from zope.schema.interfaces import ITitledTokenizedTerm
from zope.schema.interfaces import IVocabularyTokenized

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.person.interfaces import IPerson
from schooltool.group.interfaces import IGroup

from schooltool.basicperson.browser.person import PersonTerm
from schooltool.basicperson.browser.person import GroupTerm
from schooltool.basicperson.interfaces import IGroupSource
from schooltool.basicperson.interfaces import IBasicPersonSource


class Term(object):
    """Simplistic term that uses value as token.
    """
    implements(ITitledTokenizedTerm)

    def __init__(self, value):
        self.title = value
        self.token = value
        self.value = value


class GradeClassSource(object):
    implements(IGroupSource)

    def __init__(self, context):
        self.context = context

    def __len__(self):
        len(self.context.groups)

    def __contains__(self, value):
        return True

    def __iter__(self):
        if IPerson.providedBy(self.context):
            tokens = [group.__name__
                      for group in self.context.groups
                      if IGroup.providedBy(group)]
        else:
            tokens = list(ISchoolToolApplication(None)['groups'])

        for token in sorted(tokens):
            yield self.getTermByToken(token)

    def getTermByToken(self, token):
        app = ISchoolToolApplication(None)
        gc = app['groups']
        if token not in gc:
            raise LookupError(token)
        return GroupTerm(token)

    def getTerm(self, value):
        return GroupTerm(value)


def gradeClassVocabularyFactory():
    return GradeClassSource


class AdvisorSource(object):
    implements(IBasicPersonSource)

    def __init__(self, context):
        self.context = context

    def __contains__(self, value):
        return True

    def __len__(self):
        len(self.context.groups)

    def __iter__(self):
        app = ISchoolToolApplication(None)
        persons = app['groups']['teachers'].members
        for person in sorted(persons, key=lambda p: p.__name__):
            yield PersonTerm(person)

    def getTermByToken(self, token):
        app = ISchoolToolApplication(None)
        pc = app['persons']
        if token not in pc:
            raise LookupError(token)
        return PersonTerm(pc[token])

    def getTerm(self, value):
        return PersonTerm(value)


def advisorVocabularyFactory():
    return AdvisorSource
